import asyncio
import base64
import binascii
import json
import logging
import os
import threading
import time
from io import BytesIO
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
from starlette.responses import StreamingResponse

from agents.decision_agent import audit_return_request
from agents.rag_agent import advanced_retrieve
from agents.vision_agent import VisionAgent


load_dotenv()

app = FastAPI(title="AI Return Auditor Multi-Agent Backend", version="1.0")
logger = logging.getLogger(__name__)
_progress_lock = threading.Lock()
_audit_progress: dict[str, dict[str, Any]] = {}
_PROGRESS_TTL_SECONDS = 3600


class VisionStageRequest(BaseModel):
    request_id: str | None = None
    image_base64: str
    customer_description: str = Field(min_length=1)


class RAGStageRequest(BaseModel):
    request_id: str | None = None
    customer_description: str = Field(min_length=1)
    vision_agent_json: dict[str, Any]


class DecisionStageRequest(BaseModel):
    request_id: str | None = None
    order_id: str = Field(min_length=1)
    product_name: str = ""
    item_value: float = Field(default=0.0, ge=0.0)
    original_user_description: str = Field(min_length=1)
    vision_agent_json: dict[str, Any]
    rag_agent_json: dict[str, Any]


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _set_progress(request_id: str | None, stage: str, state: str, message: str) -> None:
    if not request_id:
        return
    now = time.time()
    with _progress_lock:
        expired = [
            key
            for key, value in _audit_progress.items()
            if now - value["updated_at"] > _PROGRESS_TTL_SECONDS
        ]
        for key in expired:
            del _audit_progress[key]
        entry = _audit_progress.setdefault(request_id, {"stages": {}, "updated_at": now})
        entry["stages"][stage] = {"state": state, "message": message}
        entry["updated_at"] = now


def _decode_image(image_base64: str) -> Image.Image:
    encoded_image = image_base64.split(",", 1)[-1] if image_base64.startswith("data:") else image_base64
    try:
        image_bytes = base64.b64decode(encoded_image, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="image_base64 must contain valid base64 image data.") from exc
    if not image_bytes:
        raise HTTPException(status_code=422, detail="The uploaded product image is empty.")
    try:
        with Image.open(BytesIO(image_bytes)) as uploaded_image:
            uploaded_image.load()
            return uploaded_image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"The uploaded file is not a readable image: {exc}") from exc


def _build_rag_result(customer_description: str, vision_agent_json: dict[str, Any]) -> dict[str, Any]:
    query = (
        f"Original customer description:\n{customer_description}\n\n"
        "Vision agent JSON:\n"
        f"{json.dumps(vision_agent_json, ensure_ascii=False)}"
    )
    retrieved_chunks = advanced_retrieve(query)
    policies = [
        {
            "policy_id": chunk.get("chunk_id") or chunk.get("title") or "POL-GENERAL",
            "title": chunk.get("title", ""),
            "rule": chunk["text"],
            "relevance": chunk.get("rerank_score"),
        }
        for chunk in retrieved_chunks
    ]
    return {
        "query": query,
        "applicable_policy": policies,
        "summary": "\n".join(policy["rule"] for policy in policies),
        "sources": [policy["policy_id"] for policy in policies],
        "chunks": policies,
        "retrieval_successful": bool(policies),
    }


@app.get("/api/audit-progress/{request_id}")
async def get_audit_progress(request_id: str) -> dict[str, Any]:
    with _progress_lock:
        entry = _audit_progress.get(request_id)
        return {"stages": dict(entry["stages"]) if entry else {}}


@app.post("/analyze/vision")
async def analyze_vision(request: VisionStageRequest) -> dict[str, Any]:
    _set_progress(request.request_id, "vision", "running", "Analyzing the uploaded photo against the customer description.")
    try:
        product_image = _decode_image(request.image_base64)
        analysis = await asyncio.to_thread(
            VisionAgent().analyze,
            product_image,
            request.customer_description,
        )
        result = analysis.model_dump()
        _set_progress(request.request_id, "vision", "complete", "Visual observations are ready for policy matching.")
        return result
    except HTTPException as exc:
        _set_progress(request.request_id, "vision", "failed", str(exc.detail))
        raise
    except Exception as exc:
        logger.exception("Vision agent endpoint failed")
        _set_progress(request.request_id, "vision", "failed", f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/analyze/rag")
async def analyze_rag(request: RAGStageRequest) -> dict[str, Any]:
    _set_progress(request.request_id, "rag", "running", "Searching and ranking policy passages against the claim and visual findings.")
    try:
        result = await asyncio.to_thread(
            _build_rag_result,
            request.customer_description,
            request.vision_agent_json,
        )
        _set_progress(
            request.request_id,
            "rag",
            "complete",
            f"Retrieved {len(result['chunks'])} policy passage(s).",
        )
        return result
    except Exception as exc:
        logger.exception("RAG agent endpoint failed")
        _set_progress(request.request_id, "rag", "failed", f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/analyze/decision")
async def analyze_decision(request: DecisionStageRequest) -> dict[str, Any]:
    _set_progress(
        request.request_id,
        "decision",
        "running",
        "Comparing independent recommendations and completing the local compliance review.",
    )
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        detail = "GROQ_API_KEY is not configured for decision analysis."
        _set_progress(request.request_id, "decision", "failed", detail)
        raise HTTPException(status_code=503, detail=detail)
    try:
        decision_prompt = json.dumps(
            {
                "order_id": request.order_id,
                "product_name": request.product_name,
                "item_value": request.item_value,
                "original_user_description": request.original_user_description,
                "vision_agent_json": request.vision_agent_json,
            },
            ensure_ascii=False,
        )
        rag_context = json.dumps(request.rag_agent_json.get("applicable_policy", []), ensure_ascii=False)
        result = await audit_return_request(
            groq_api_key,
            decision_prompt,
            rag_context,
            item_value=request.item_value,
        )
        output = {
            **result,
            "reasoning_summary": result.get("reasoning_summary") or result.get("reasoning"),
            "reason": result.get("reasoning"),
            "evidence_chain": {
                "vision_agent": request.vision_agent_json,
                "retrieved_policies": request.rag_agent_json.get("applicable_policy", []),
            },
        }
        _set_progress(
            request.request_id,
            "decision",
            "complete",
            f"Final decision produced: {output.get('decision', 'unknown')}.",
        )
        return output
    except Exception as exc:
        logger.exception("Decision agent endpoint failed")
        _set_progress(request.request_id, "decision", "failed", f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc


async def audit_pipeline_events(
    order_id: str,
    user_description: str,
    item_value: float,
    product_name: str,
    image: UploadFile,
) -> AsyncIterator[dict]:
    """Yield real stage updates followed by the completed audit result."""
    order_id = order_id.strip()
    user_description = user_description.strip()
    product_name = product_name.strip()

    if not order_id or not user_description:
        yield {
            "type": "error",
            "stage": "input",
            "status_code": 422,
            "detail": "Order ID and a customer description are required.",
        }
        return

    if not os.getenv("GEMINI_API_KEY"):
        yield {
            "type": "error",
            "stage": "configuration",
            "status_code": 503,
            "detail": "GEMINI_API_KEY is not configured for vision analysis.",
        }
        return
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        yield {
            "type": "error",
            "stage": "configuration",
            "status_code": 503,
            "detail": "GROQ_API_KEY is not configured for policy retrieval and decision analysis.",
        }
        return

    image_bytes = await image.read()
    if not image_bytes:
        yield {
            "type": "error",
            "stage": "input",
            "status_code": 422,
            "detail": "The uploaded product image is empty.",
        }
        return

    try:
        with Image.open(BytesIO(image_bytes)) as uploaded_image:
            uploaded_image.load()
            product_image = uploaded_image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        yield {
            "type": "error",
            "stage": "input",
            "status_code": 422,
            "detail": f"The uploaded file is not a readable image: {exc}",
        }
        return

    yield {
        "type": "progress",
        "stage": "vision",
        "state": "running",
        "message": "Comparing the uploaded product photo with the customer's description.",
    }
    try:
        vision_analysis = await asyncio.to_thread(
            VisionAgent().analyze,
            product_image,
            user_description,
        )
    except Exception as exc:
        logger.exception("Vision agent failed")
        yield {
            "type": "error",
            "stage": "vision",
            "status_code": 502,
            "detail": f"{type(exc).__name__}: {exc}",
        }
        return

    vision_result = vision_analysis.model_dump()
    yield {
        "type": "progress",
        "stage": "vision",
        "state": "complete",
        "message": "Visual observations are ready for policy matching.",
    }
    rag_query = (
        f"Original customer description:\n{user_description}\n\n"
        "Vision agent JSON:\n"
        f"{json.dumps(vision_result, ensure_ascii=False)}"
    )

    yield {
        "type": "progress",
        "stage": "rag",
        "state": "running",
        "message": "Searching and ranking return-policy passages against the description and vision findings.",
    }
    try:
        retrieved_chunks = await asyncio.to_thread(advanced_retrieve, rag_query)
    except Exception as exc:
        logger.exception("Policy retrieval failed")
        yield {
            "type": "error",
            "stage": "rag",
            "status_code": 502,
            "detail": f"{type(exc).__name__}: {exc}",
        }
        return

    rag_policies = [
        {
            "policy_id": chunk.get("chunk_id") or chunk.get("title") or "POL-GENERAL",
            "title": chunk.get("title", ""),
            "rule": chunk["text"],
            "relevance": chunk.get("rerank_score"),
        }
        for chunk in retrieved_chunks
    ]
    yield {
        "type": "progress",
        "stage": "rag",
        "state": "complete",
        "message": f"Retrieved {len(rag_policies)} policy passage(s).",
    }

    decision_prompt = json.dumps(
        {
            "order_id": order_id,
            "product_name": product_name,
            "item_value": item_value,
            "original_user_description": user_description,
            "vision_agent_json": vision_result,
        },
        ensure_ascii=False,
    )
    rag_context = json.dumps(rag_policies, ensure_ascii=False)

    yield {
        "type": "progress",
        "stage": "decision",
        "state": "running",
        "message": "Comparing independent recommendations and completing the local compliance review.",
    }
    try:
        decision_result = await audit_return_request(
            groq_api_key,
            decision_prompt,
            rag_context,
            item_value=item_value,
        )
    except Exception as exc:
        logger.exception("Decision agent failed")
        yield {
            "type": "error",
            "stage": "decision",
            "status_code": 502,
            "detail": f"{type(exc).__name__}: {exc}",
        }
        return

    decision_output = {
        **decision_result,
        "reasoning_summary": decision_result.get("reasoning_summary")
        or decision_result.get("reasoning"),
    }

    result = {
        "status": "success",
        "pipeline_trace": {
            "vision_agent": vision_result,
            "rag_agent": rag_policies,
            "decision_output": decision_output,
        },
    }
    yield {
        "type": "progress",
        "stage": "decision",
        "state": "complete",
        "message": f"Final decision produced: {decision_output.get('decision', 'unknown')}.",
    }
    yield {"type": "complete", "result": result}


@app.post("/api/audit-pipeline")
async def run_audit_pipeline(
    order_id: str = Form(..., min_length=1),
    user_description: str = Form(..., min_length=1),
    item_value: float = Form(0.0, ge=0.0),
    product_name: str = Form(""),
    image: UploadFile = File(...),
) -> dict:
    """Run the complete audit and return a JSON result."""
    async for event in audit_pipeline_events(
        order_id,
        user_description,
        item_value,
        product_name,
        image,
    ):
        if event["type"] == "error":
            raise HTTPException(
                status_code=event["status_code"],
                detail=f"{event['stage'].title()} stage failed: {event['detail']}",
            )
        if event["type"] == "complete":
            return event["result"]

    raise HTTPException(status_code=500, detail="Audit ended without a result.")


@app.post("/api/audit-pipeline/stream")
async def stream_audit_pipeline(
    order_id: str = Form(..., min_length=1),
    user_description: str = Form(..., min_length=1),
    item_value: float = Form(0.0, ge=0.0),
    product_name: str = Form(""),
    image: UploadFile = File(...),
) -> StreamingResponse:
    """Stream actual pipeline stage updates using server-sent events."""
    async def events() -> AsyncIterator[str]:
        async for event in audit_pipeline_events(
            order_id,
            user_description,
            item_value,
            product_name,
            image,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("appBack:app", host="0.0.0.0", port=8000, reload=True)
