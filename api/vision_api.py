
import base64
import binascii
import io

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from agents.vision_agent import VisionAgent

app = FastAPI(title="AI Return Auditor - Vision API")


class VisionRequest(BaseModel):
    image_base64: str = Field(min_length=1)
    customer_description: str = Field(min_length=1)


class OrderExtractionRequest(BaseModel):
    document_base64: str = Field(min_length=1)


@app.post("/analyze")
def analyze(request: VisionRequest):
    try:
        image_bytes = base64.b64decode(
            request.image_base64,
            validate=True,
        )

        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            image = source.convert("RGB")

        agent = VisionAgent()
        result = agent.analyze(
            image=image,
            customer_description=request.customer_description,
        )

        return {
            "result": result.model_dump(),
            "state": agent.get_state().model_dump(),
        }

    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid image data.",
        ) from exc

    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Vision analysis failed.",
        ) from exc


@app.post("/extract-order")
def extract_order(request: OrderExtractionRequest):
    try:
        document_bytes = base64.b64decode(
            request.document_base64,
            validate=True,
        )

        with Image.open(io.BytesIO(document_bytes)) as source:
            source.load()
            document_image = source.convert("RGB")

        agent = VisionAgent()

        result = agent.extract_order_information(
            document_image=document_image
        )

        return {
            "result": result.model_dump(),
        }

    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document image data.",
        ) from exc

    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded document is not a valid image.",
        ) from exc

    except Exception as exc:
      print(f"[Order Extraction Error] {type(exc).__name__}: {exc}")
      raise HTTPException(
        status_code=500,
        detail=f"Order extraction failed: {exc}",
      ) from exc
