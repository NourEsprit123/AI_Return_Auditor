"""
services/api.py
---------------
FastAPI server — HTTP bridge between n8n and the Python agents.

Exposes three endpoints that n8n calls sequentially:

  POST /analyze/vision    → Agent 1 (Vision Agent)
  POST /analyze/rag       → Agent 2 (RAG Agent)
  POST /analyze/decision  → Agent 3 (Decision Agent)
  POST /analyze/full      → Full pipeline in one call (convenience)
  GET  /health            → Health check for n8n

n8n cannot run Python directly. This server makes each agent
callable via HTTP, which is what n8n HTTP Request nodes require.

Run with:
  uvicorn services.api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import base64
import io
import traceback

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from PIL import Image

from agents.vision_agent import VisionAgent, VisionAnalysis
from agents.rag_agent import RAGAgent
from agents.decision_agent import DecisionAgent
from rag.retriever import PolicyResult, RetrievedChunk
from services.order_service import get_order, build_order_from_session


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AI Return Auditor — Agent API",
    description=(
        "HTTP API exposing Vision, RAG, and Decision agents "
        "for orchestration by n8n."
    ),
    version="1.0.0",
)

# Allow n8n (running on localhost or Docker) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LAZY-LOADED AGENTS (initialised on first request)
# ============================================================

_vision_agent: Optional[VisionAgent] = None
_rag_agent: Optional[RAGAgent] = None
_decision_agent: Optional[DecisionAgent] = None


def get_vision_agent() -> VisionAgent:
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = VisionAgent()
    return _vision_agent


def get_rag_agent() -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent


def get_decision_agent() -> DecisionAgent:
    global _decision_agent
    if _decision_agent is None:
        _decision_agent = DecisionAgent()
    return _decision_agent


# ============================================================
# REQUEST / RESPONSE SCHEMAS
# ============================================================

class VisionRequest(BaseModel):
    """
    Input for /analyze/vision.
    The image is base64-encoded so it can travel in JSON.
    n8n passes the image as a base64 string from the webhook payload.
    """
    image_base64: str
    customer_description: str


class VisionResponse(BaseModel):
    product_category: str
    product_type: str
    damage_type: str
    damage_location: str
    severity: str
    confidence: float
    visual_evidence: str
    description_consistency: str
    uncertainty: str
    agent_status: str


class RAGRequest(BaseModel):
    """
    Input for /analyze/rag.
    Receives the VisionAnalysis fields directly — no image needed.
    """
    product_category: str
    product_type: str
    damage_type: str
    damage_location: str
    severity: str
    confidence: float
    visual_evidence: str
    description_consistency: str
    uncertainty: str


class ChunkSchema(BaseModel):
    text: str
    source: str
    doc_type: str
    relevance_score: float


class RAGResponse(BaseModel):
    query: str
    applicable_policy: str
    summary: str
    sources: list[str]
    chunks: list[ChunkSchema]
    retrieval_successful: bool


class DecisionRequest(BaseModel):
    """
    Input for /analyze/decision.
    Receives Vision + RAG outputs + order_id to look up order info.
    """
    # Vision fields
    product_category: str
    product_type: str
    damage_type: str
    damage_location: str
    severity: str
    confidence: float
    visual_evidence: str
    description_consistency: str
    uncertainty: str

    # RAG fields
    rag_query: str
    applicable_policy: str
    policy_summary: str
    policy_sources: list[str]
    policy_chunks: list[ChunkSchema]
    retrieval_successful: bool

    # Order
    order_id: str
    product_name: Optional[str] = ""
    product_category_order: Optional[str] = ""
    purchase_price: Optional[float] = 0.0
    delivery_status: Optional[str] = "Delivered"


class DecisionResponse(BaseModel):
    decision: str
    confidence: float
    risk_level: str
    reason: str
    guardrail_hit: str
    evidence_chain: list[str]
    reasoning_steps: str


class FullPipelineRequest(BaseModel):
    """
    Input for /analyze/full — runs all 3 agents in sequence.
    This is the endpoint n8n calls from its webhook trigger.
    """
    image_base64: str
    customer_description: str
    order_id: str
    product_name: Optional[str] = ""
    product_category: Optional[str] = ""
    purchase_price: Optional[float] = 0.0
    delivery_status: Optional[str] = "Delivered"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    class Config:
        # Allow coercion from string to float etc.
        coerce_numbers_to_str = False

    def __init__(self, **data):
        # Coerce purchase_price from string to float if needed
        if "purchase_price" in data and isinstance(data["purchase_price"], str):
            try:
                data["purchase_price"] = float(data["purchase_price"].strip())
            except (ValueError, AttributeError):
                data["purchase_price"] = 0.0
        # Strip leading = signs that n8n might add
        for key in ["customer_description", "order_id", "product_name",
                    "product_category", "delivery_status"]:
            if key in data and isinstance(data[key], str):
                data[key] = data[key].lstrip("=").strip()
        super().__init__(**data)


class FullPipelineResponse(BaseModel):
    # Vision
    vision: VisionResponse
    # RAG
    rag: RAGResponse
    # Decision
    decision: DecisionResponse
    # Meta
    pipeline_status: str
    error: Optional[str] = None


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    """Health check endpoint — n8n pings this to verify the server is up."""
    return {"status": "ok", "service": "AI Return Auditor API"}


# ============================================================
# ENDPOINT 1 — VISION AGENT
# ============================================================

@app.post("/analyze/vision", response_model=VisionResponse)
def analyze_vision(request: VisionRequest):
    """
    Agent 1 — Multimodal Vision Agent.

    Accepts a base64-encoded image and customer description.
    Returns structured VisionAnalysis.

    Called by n8n HTTP Request node after the webhook trigger.
    """
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(request.image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        agent = get_vision_agent()
        result: VisionAnalysis = agent.analyze(
            image=image,
            customer_description=request.customer_description,
        )

        state = agent.get_state()

        return VisionResponse(
            product_category=result.product_category,
            product_type=result.product_type,
            damage_type=result.damage_type,
            damage_location=result.damage_location,
            severity=result.severity,
            confidence=result.confidence,
            visual_evidence=result.visual_evidence,
            description_consistency=result.description_consistency,
            uncertainty=result.uncertainty,
            agent_status=state.status,
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ENDPOINT 2 — RAG AGENT
# ============================================================

@app.post("/analyze/rag", response_model=RAGResponse)
def analyze_rag(request: RAGRequest):
    """
    Agent 2 — Policy RAG Agent (Modular RAG).

    Accepts VisionAnalysis fields.
    Returns structured PolicyResult with retrieved chunks and LLM synthesis.

    Called by n8n after the Vision Agent step.
    """
    try:
        vision = VisionAnalysis(
            product_category=request.product_category,
            product_type=request.product_type,
            damage_type=request.damage_type,
            damage_location=request.damage_location,
            severity=request.severity,
            confidence=request.confidence,
            visual_evidence=request.visual_evidence,
            description_consistency=request.description_consistency,
            uncertainty=request.uncertainty,
        )

        agent = get_rag_agent()
        result: PolicyResult = agent.retrieve_policy(vision)

        return RAGResponse(
            query=result.query,
            applicable_policy=result.applicable_policy,
            summary=result.summary,
            sources=result.sources,
            chunks=[
                ChunkSchema(
                    text=c.text,
                    source=c.source,
                    doc_type=c.doc_type,
                    relevance_score=c.relevance_score,
                )
                for c in result.chunks
            ],
            retrieval_successful=result.retrieval_successful,
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ENDPOINT 3 — DECISION AGENT
# ============================================================

@app.post("/analyze/decision", response_model=DecisionResponse)
def analyze_decision(request: DecisionRequest):
    """
    Agent 3 — Claim Evaluator & Decision Agent.

    Accepts Vision + RAG outputs and order info.
    Returns final DecisionResult (APPROVED or HUMAN_REVIEW).

    Called by n8n after the RAG Agent step.
    """
    try:
        # Reconstruct VisionAnalysis
        vision = VisionAnalysis(
            product_category=request.product_category,
            product_type=request.product_type,
            damage_type=request.damage_type,
            damage_location=request.damage_location,
            severity=request.severity,
            confidence=request.confidence,
            visual_evidence=request.visual_evidence,
            description_consistency=request.description_consistency,
            uncertainty=request.uncertainty,
        )

        # Reconstruct PolicyResult
        chunks = [
            RetrievedChunk(
                text=c.text,
                source=c.source,
                doc_type=c.doc_type,
                chunk_id=i,
                relevance_score=c.relevance_score,
            )
            for i, c in enumerate(request.policy_chunks)
        ]
        policy = PolicyResult(
            query=request.rag_query,
            chunks=chunks,
            sources=request.policy_sources,
            summary=request.policy_summary,
            applicable_policy=request.applicable_policy,
            retrieval_successful=request.retrieval_successful,
        )

        # Look up order from CSV, fallback to request fields
        order = get_order(request.order_id)
        if not order["found"]:
            order.update({
                "product_name":     request.product_name,
                "product_category": request.product_category_order,
                "purchase_price":   request.purchase_price,
                "delivery_status":  request.delivery_status,
                "within_return_window": request.delivery_status == "Delivered",
            })

        agent = get_decision_agent()
        result = agent.decide(vision, policy, order)

        return DecisionResponse(
            decision=result.decision,
            confidence=result.confidence,
            risk_level=result.risk_level,
            reason=result.reason,
            guardrail_hit=result.guardrail_hit,
            evidence_chain=result.evidence_chain,
            reasoning_steps=result.reasoning_steps,
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ENDPOINT 4 — FULL PIPELINE (single n8n call)
# ============================================================

@app.post("/analyze/full", response_model=FullPipelineResponse)
def analyze_full(request: FullPipelineRequest):
    """
    Full pipeline — runs all 3 agents in sequence in one HTTP call.

    This is the primary endpoint called by n8n's webhook trigger.
    n8n sends the claim data here and receives the complete result
    including vision analysis, policy retrieval, and final decision.

    n8n then uses the decision field to branch:
      APPROVED     → log + notify customer
      HUMAN_REVIEW → alert human reviewer + flag claim
    """
    try:
        # ---- Agent 1: Vision ----
        image_bytes = base64.b64decode(request.image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        vision_agent = get_vision_agent()
        vision_result: VisionAnalysis = vision_agent.analyze(
            image=image,
            customer_description=request.customer_description,
        )
        vision_state = vision_agent.get_state()

        # ---- Agent 2: RAG ----
        rag_agent = get_rag_agent()
        policy_result: PolicyResult = rag_agent.retrieve_policy(vision_result)

        # ---- Order lookup ----
        order = get_order(request.order_id)
        if not order["found"]:
            order.update({
                "product_name":       request.product_name,
                "product_category":   request.product_category,
                "purchase_price":     request.purchase_price,
                "delivery_status":    request.delivery_status,
                "within_return_window": request.delivery_status == "Delivered",
            })

        # ---- Agent 3: Decision ----
        decision_agent = get_decision_agent()
        decision_result = decision_agent.decide(
            vision_result,
            policy_result,
            order,
        )

        return FullPipelineResponse(
            vision=VisionResponse(
                product_category=vision_result.product_category,
                product_type=vision_result.product_type,
                damage_type=vision_result.damage_type,
                damage_location=vision_result.damage_location,
                severity=vision_result.severity,
                confidence=vision_result.confidence,
                visual_evidence=vision_result.visual_evidence,
                description_consistency=vision_result.description_consistency,
                uncertainty=vision_result.uncertainty,
                agent_status=vision_state.status,
            ),
            rag=RAGResponse(
                query=policy_result.query,
                applicable_policy=policy_result.applicable_policy,
                summary=policy_result.summary,
                sources=policy_result.sources,
                chunks=[
                    ChunkSchema(
                        text=c.text,
                        source=c.source,
                        doc_type=c.doc_type,
                        relevance_score=c.relevance_score,
                    )
                    for c in policy_result.chunks
                ],
                retrieval_successful=policy_result.retrieval_successful,
            ),
            decision=DecisionResponse(
                decision=decision_result.decision,
                confidence=decision_result.confidence,
                risk_level=decision_result.risk_level,
                reason=decision_result.reason,
                guardrail_hit=decision_result.guardrail_hit,
                evidence_chain=decision_result.evidence_chain,
                reasoning_steps=decision_result.reasoning_steps,
            ),
            pipeline_status="completed",
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
