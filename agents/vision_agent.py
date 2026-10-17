import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from PIL import Image
from pydantic import BaseModel, Field


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "vision_agent_v1.txt"
)


# ============================================================
# CONFIGURATION
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv(
    "GEMINI_VISION_MODEL",
    "gemini-3.8-flash"
)


# ============================================================
# STRUCTURED OUTPUT
# ============================================================

class VisionAnalysis(BaseModel):

    product_category: str = Field(
        description="General product category."
    )

    product_type: str = Field(
        description="Specific product type identified from the image."
    )

    damage_type: str = Field(
        description="Visible damage or defect."
    )

    damage_location: str = Field(
        description="Location of the visible damage."
    )

    severity: str = Field(
        description=(
            "Damage severity: Low, Medium, High, None, or Unknown."
        )
    )

    confidence: float = Field(
        description="Confidence between 0 and 1.",
        ge=0.0,
        le=1.0
    )

    visual_evidence: str = Field(
        description="What is visibly observed in the image."
    )

    description_consistency: str = Field(
        description=(
            "Whether the visual evidence is consistent "
            "with the customer description."
        )
    )

    uncertainty: str = Field(
        description="Important uncertainty or ambiguity."
    )


# ============================================================
# VISION AGENT
# ============================================================

class VisionAgent:

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):

        self.api_key = (
            api_key
            or API_KEY
        )

        self.model_name = (
            model_name
            or MODEL_NAME
        )

        if not self.api_key:

            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

        self.prompt = self._load_prompt()

    # ========================================================
    # LOAD PROMPT
    # ========================================================

    def _load_prompt(self) -> str:

        if not PROMPT_PATH.exists():

            raise FileNotFoundError(
                f"Prompt file not found: {PROMPT_PATH}"
            )

        return PROMPT_PATH.read_text(
            encoding="utf-8"
        )

    # ========================================================
    # ANALYZE IMAGE
    # ========================================================

    def analyze(
        self,
        image: Image.Image,
        customer_description: str
    ) -> VisionAnalysis:

        if image is None:

            raise ValueError(
                "An image is required."
            )

        if not customer_description.strip():

            raise ValueError(
                "Customer description is required."
            )

        # ----------------------------------------------------
        # BUILD PROMPT
        # ----------------------------------------------------

        user_prompt = f"""
{self.prompt}

CUSTOMER DESCRIPTION:
{customer_description}

Analyze the provided product image and return
the structured VisionAnalysis result.
"""

        # ----------------------------------------------------
        # MODELS FALLBACK
        # ----------------------------------------------------

        models_to_try = [
            self.model_name,
            "gemini-3.7-flash",
            "gemini-3.6-flash"
        ]

        response = None
        errors = []

        # ----------------------------------------------------
        # TRY EACH MODEL
        # ----------------------------------------------------

        for model_name in models_to_try:

            try:

                response = self.client.models.generate_content(

                    model=model_name,

                    contents=[
                        user_prompt,
                        image
                    ],

                    config={
                        "response_mime_type": "application/json",
                        "response_schema": VisionAnalysis
                    }
                )

                break

            except Exception as exc:

                errors.append(
                    f"{model_name}: {exc}"
                )

                continue

        # ----------------------------------------------------
        # ALL MODELS FAILED
        # ----------------------------------------------------

        if response is None:

            raise RuntimeError(
                "All Gemini Vision models failed.\n\n"
                + "\n".join(errors)
            )

        # ----------------------------------------------------
        # STRUCTURED RESPONSE
        # ----------------------------------------------------

        parsed = getattr(response, "parsed", None)

        if parsed is not None:

            return VisionAnalysis.model_validate(parsed)

        # ----------------------------------------------------
        # JSON FALLBACK
        # ----------------------------------------------------

        response_text = getattr(response, "text", None)

        if response_text:

            try:

                return VisionAnalysis.model_validate_json(
                    response_text
                )

            except Exception as exc:

                raise RuntimeError(
                    "Gemini returned a response, but it "
                    "could not be converted to VisionAnalysis."
                ) from exc

        # ----------------------------------------------------
        # EMPTY RESPONSE
        # ----------------------------------------------------

        raise RuntimeError(
            "Gemini returned an empty response."
        )