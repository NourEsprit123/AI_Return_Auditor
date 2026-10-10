
import os
import time
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

PROMPT_PATH = BASE_DIR / "prompts" / "vision_agent_v1.txt"


# ============================================================
# CONFIGURATION
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv(
    "GEMINI_VISION_MODEL",
    "gemini-3.1-flash-lite",
)

CONFIDENCE_THRESHOLD = 0.80
MAX_ATTEMPTS = 3
MAX_MODEL_RETRIES = 2
RETRY_DELAY_SECONDS = 3


# ============================================================
# STRUCTURED VISION RESULT
# ============================================================

class VisionAnalysis(BaseModel):

    product_category: str = Field(
        description="General product category."
    )

    product_type: str = Field(
        description="Specific product type identified from the image."
    )

    damage_type: str = Field(
        description="Visible damage or defect, described clearly."
    )

    damage_location: str = Field(
        description="Location of the visible damage, described clearly."
    )

    severity: str = Field(
        description=(
            "Damage severity: Low, Medium, High, None, or Unknown."
        )
    )

    confidence: float = Field(
        description="Confidence between 0 and 1.",
        ge=0.0,
        le=1.0,
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
# AGENT STATE
# ============================================================

class VisionAgentState(BaseModel):

    attempt: int = 0
    status: str = "STARTING"
    reason: str = ""
    confidence: float = 0.0
    needs_reanalysis: bool = True

    final_result: Optional[VisionAnalysis] = None
    previous_result: Optional[VisionAnalysis] = None

    last_action: str = ""

    reasoning_history: list[str] = Field(default_factory=list)
    action_history: list[str] = Field(default_factory=list)
    model_history: list[str] = Field(default_factory=list)


# ============================================================
# VISION AGENT
# ============================================================

class VisionAgent:
    """
    Multimodal product damage analysis agent.

    OBSERVE -> REASON -> PLAN -> ACTION
                    ^              |
                    |______________|

    The agent finishes with ACCEPT or ESCALATE.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):

        self.api_key = api_key or API_KEY
        self.model_name = model_name or MODEL_NAME

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.prompt = self._load_prompt()
        self.state = VisionAgentState()
        self.active_model = self.model_name

    # ========================================================
    # LOAD PROMPT
    # ========================================================

    def _load_prompt(self) -> str:

        if not PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {PROMPT_PATH}"
            )

        return PROMPT_PATH.read_text(encoding="utf-8")

    # ========================================================
    # MODEL LIST
    # ========================================================

    def _get_models_to_try(self) -> list[str]:

        models = [
            self.active_model,
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ]

        return list(dict.fromkeys(models))

    # ========================================================
    # TEMPORARY ERROR DETECTION
    # ========================================================

    def _is_temporary_error(self, error: Exception) -> bool:

        error_text = str(error).lower()

        temporary_indicators = [
            "503",
            "unavailable",
            "high demand",
            "temporarily",
            "overloaded",
            "resource exhausted",
            "429",
            "rate limit",
        ]

        return any(
            indicator in error_text
            for indicator in temporary_indicators
        )

    # ========================================================
    # MULTIMODAL ANALYSIS
    # ========================================================

    def _analyze_image(
        self,
        image: Image.Image,
        customer_description: str,
        attempt: int,
        previous_reasoning: str = "",
        next_action: str = "",
    ) -> VisionAnalysis:

        if attempt == 1:

            analysis_instruction = """
Perform the initial visual analysis.

Inspect the complete image carefully.

Identify:
- product category;
- product type;
- visible damage;
- damage location;
- severity;
- confidence;
- visual evidence;
- consistency with the customer description;
- uncertainty.

The image is the primary visual evidence.
Do not assume that the customer's description is correct.
"""

        elif next_action == "VERIFY_PRODUCT_IDENTITY":

            analysis_instruction = f"""
This is a targeted product identity verification.

Previous agent reasoning:
{previous_reasoning}

Focus on:
1. What physical object is visible?
2. What product category and type are visible?
3. Is the product mentioned by the customer present?
4. Does the image show a different product?
5. Is there evidence of a mismatch?

Reinspect the image independently.
"""

        elif next_action == "VERIFY_DAMAGE":

            analysis_instruction = f"""
This is a targeted damage verification.

Previous agent reasoning:
{previous_reasoning}

Focus on:
1. What damage or defect is actually visible?
2. Where exactly is the damage?
3. Is the claimed damage visible?
4. What visual evidence supports the conclusion?
5. What remains uncertain?

Inspect the image independently.
"""

        elif next_action == "VERIFY_DESCRIPTION_CONSISTENCY":

            analysis_instruction = f"""
This is a targeted customer-description verification.

Previous agent reasoning:
{previous_reasoning}

Customer description:
{customer_description}

Determine:
1. Does the described product appear in the image?
2. Does the claimed damage appear in the image?
3. Is the damage location compatible?
4. Is there a contradiction?
5. Is the description supported or unsupported?
6. Is the claim impossible to verify visually?

Do not assume that the customer's description is correct.
"""

        else:

            analysis_instruction = f"""
This is the final verification attempt.

Previous agent reasoning:
{previous_reasoning}

Independently verify:
- product identity;
- visible damage and location;
- customer description;
- consistency and contradictions;
- uncertainty.

If the customer's description does not match the image,
mark the evidence as inconsistent.

Only report information supported by the image.
"""

        user_prompt = f"""
{self.prompt}

============================================================
CURRENT AGENT TASK
============================================================

{analysis_instruction}

============================================================
CUSTOMER DESCRIPTION
============================================================

{customer_description}

============================================================
AGENT ATTEMPT
============================================================

{attempt}

============================================================
PREVIOUS AGENT REASONING
============================================================

{
    previous_reasoning
    if previous_reasoning
    else "No previous reasoning. This is the initial observation."
}

============================================================
OUTPUT
============================================================

Return only the structured VisionAnalysis result.
"""

        models_to_try = self._get_models_to_try()

        response = None
        successful_model = None
        errors = []

        for model_name in models_to_try:

            retry_count = 0

            while retry_count <= MAX_MODEL_RETRIES:

                try:

                    print(
                        f"[Vision Agent] Attempt {attempt} | "
                        f"Model: {model_name}"
                    )

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[user_prompt, image],
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": VisionAnalysis,
                        },
                    )

                    successful_model = model_name
                    break

                except Exception as exc:

                    errors.append(f"{model_name}: {exc}")

                    print(
                        f"[Vision Agent] Model failed: {model_name}"
                    )

                    if self._is_temporary_error(exc):

                        retry_count += 1

                        if retry_count <= MAX_MODEL_RETRIES:

                            print(
                                "[Vision Agent] Temporary error. "
                                f"Retry {retry_count}/"
                                f"{MAX_MODEL_RETRIES} in "
                                f"{RETRY_DELAY_SECONDS}s..."
                            )

                            time.sleep(RETRY_DELAY_SECONDS)
                            continue

                    break

            if response is not None:
                break

        if response is None:

            raise RuntimeError(
                "All Gemini vision models failed.\n\n"
                "The API may be temporarily unavailable.\n\n"
                + "\n".join(errors)
            )

        if successful_model:

            self.active_model = successful_model
            self.state.model_history.append(successful_model)

        if getattr(response, "parsed", None):
            return response.parsed

        if getattr(response, "text", None):

            try:
                return VisionAnalysis.model_validate_json(response.text)

            except Exception as exc:

                raise RuntimeError(
                    "Gemini returned a response, but it could not "
                    "be converted to VisionAnalysis."
                ) from exc

        raise RuntimeError("Gemini returned an empty response.")

    # ========================================================
    # REASONING
    # ========================================================

    def _reason_about_result(
        self,
        result: VisionAnalysis,
        customer_description: str,
        attempt: int,
    ) -> str:

        confidence = result.confidence
        consistency = (result.description_consistency or "").lower()
        uncertainty = (result.uncertainty or "").strip()

        is_inconsistent = (
            "inconsistent" in consistency
            or "contradict" in consistency
            or "does not match" in consistency
            or "not match" in consistency
            or "unsupported" in consistency
        )

        is_consistent = (
            "consistent" in consistency and not is_inconsistent
        )

        previous_action = (
            self.state.action_history[-1]
            if self.state.action_history
            else ""
        )

        if attempt == 1:

            if is_inconsistent:
                return (
                    "Initial observation: the visual evidence "
                    "contradicts the customer description. "
                    f"The image identifies {result.product_type}, "
                    "while the description may refer to a different "
                    "product or damage. The agent must verify "
                    "the visible product identity."
                )

            if confidence < CONFIDENCE_THRESHOLD:
                return (
                    "Initial observation: confidence is below "
                    "the required threshold. Targeted verification "
                    "is required."
                )

            if is_consistent:
                return (
                    "Initial observation: the product, damage, "
                    "and customer description appear consistent."
                )

            return (
                "Initial observation: additional verification "
                "is required before completion."
            )

        if previous_action == "VERIFY_PRODUCT_IDENTITY":

            if is_inconsistent:
                return (
                    "Product identity verification completed. "
                    f"The visible product is {result.product_type}. "
                    "The description appears inconsistent with "
                    "the visible product. The agent must now "
                    "verify the damage independently."
                )

            return (
                "Product identity verification completed. "
                f"The visible product is {result.product_type}. "
                "The agent will now verify the damage."
            )

        if previous_action == "VERIFY_DAMAGE":

            if is_inconsistent:
                return (
                    "Damage verification completed. The image shows "
                    f"{result.damage_type} at {result.damage_location}. "
                    "The reported problem appears inconsistent "
                    "with the image. The contradiction remains."
                )

            if confidence >= CONFIDENCE_THRESHOLD:
                return (
                    "Damage verification completed. The visible "
                    f"damage is {result.damage_type}, with "
                    f"{confidence:.0%} confidence."
                )

            return (
                "Damage verification completed, but the evidence "
                "remains uncertain."
            )

        if previous_action == "VERIFY_DESCRIPTION_CONSISTENCY":

            if is_inconsistent:
                return (
                    "Description verification completed. The image "
                    "does not visually support the customer's claim. "
                    "The contradiction remains."
                )

            return (
                "Description verification completed. The evidence "
                "appears consistent with the customer's description."
            )

        if previous_action == "FINAL_VERIFICATION":

            if is_inconsistent:
                return (
                    "Final verification completed. The contradiction "
                    "remains, so the case must be escalated."
                )

            if confidence >= CONFIDENCE_THRESHOLD and is_consistent:
                return (
                    "Final verification completed. The visual evidence "
                    "is sufficiently reliable and consistent."
                )

            return (
                "Final verification completed, but the evidence "
                "is insufficient for automatic completion."
            )

        if confidence < 0.50:
            return (
                "The visual analysis has low confidence. "
                "Another targeted observation is required."
            )

        if uncertainty:
            return (
                "Uncertainty remains after the visual analysis. "
                "The agent must verify the uncertain element."
            )

        if confidence < CONFIDENCE_THRESHOLD:
            return (
                "Confidence is below the required threshold. "
                "Another targeted verification is required."
            )

        return (
            "Additional verification is required before completion."
        )

    # ========================================================
    # DECISION / PLANNING
    # ========================================================

    def _decide_next_action(
        self,
        result: VisionAnalysis,
        reasoning: str,
        attempt: int,
    ) -> str:

        consistency = (result.description_consistency or "").lower()
        uncertainty = (result.uncertainty or "").strip()
        confidence = result.confidence

        is_inconsistent = (
            "inconsistent" in consistency
            or "contradict" in consistency
            or "does not match" in consistency
            or "not match" in consistency
            or "unsupported" in consistency
        )

        is_consistent = (
            "consistent" in consistency and not is_inconsistent
        )

        if (
            confidence >= CONFIDENCE_THRESHOLD
            and is_consistent
            and not uncertainty
        ):
            return "ACCEPT"

        if attempt >= MAX_ATTEMPTS:
            return "ESCALATE"

        if is_inconsistent:

            if "VERIFY_PRODUCT_IDENTITY" not in self.state.action_history:
                return "VERIFY_PRODUCT_IDENTITY"

            if "VERIFY_DAMAGE" not in self.state.action_history:
                return "VERIFY_DAMAGE"

            if (
                "VERIFY_DESCRIPTION_CONSISTENCY"
                not in self.state.action_history
            ):
                return "VERIFY_DESCRIPTION_CONSISTENCY"

            return "FINAL_VERIFICATION"

        if confidence < CONFIDENCE_THRESHOLD:

            if "VERIFY_PRODUCT_IDENTITY" not in self.state.action_history:
                return "VERIFY_PRODUCT_IDENTITY"

            if "VERIFY_DAMAGE" not in self.state.action_history:
                return "VERIFY_DAMAGE"

            return "FINAL_VERIFICATION"

        if uncertainty:

            if "VERIFY_DAMAGE" not in self.state.action_history:
                return "VERIFY_DAMAGE"

            return "FINAL_VERIFICATION"

        if "VERIFY_PRODUCT_IDENTITY" not in self.state.action_history:
            return "VERIFY_PRODUCT_IDENTITY"

        if "VERIFY_DAMAGE" not in self.state.action_history:
            return "VERIFY_DAMAGE"

        return "FINAL_VERIFICATION"

    # ========================================================
    # MAIN AGENT LOOP
    # ========================================================

    def analyze(
        self,
        image: Image.Image,
        customer_description: str,
    ) -> VisionAnalysis:

        if image is None:
            raise ValueError("An image is required.")

        if not customer_description.strip():
            raise ValueError("Customer description is required.")

        self.state = VisionAgentState()

        current_result = None
        previous_reasoning = ""
        next_action = ""

        while self.state.attempt < MAX_ATTEMPTS:

            self.state.attempt += 1
            attempt = self.state.attempt
            self.state.status = "ANALYZING"

            current_result = self._analyze_image(
                image=image,
                customer_description=customer_description,
                attempt=attempt,
                previous_reasoning=previous_reasoning,
                next_action=next_action,
            )

            self.state.confidence = current_result.confidence
            self.state.previous_result = current_result

            reasoning = self._reason_about_result(
                result=current_result,
                customer_description=customer_description,
                attempt=attempt,
            )

            self.state.reasoning_history.append(reasoning)

            action = self._decide_next_action(
                result=current_result,
                reasoning=reasoning,
                attempt=attempt,
            )

            self.state.last_action = action
            self.state.action_history.append(action)

            if action == "ACCEPT":

                self.state.status = "COMPLETED"
                self.state.reason = reasoning
                self.state.needs_reanalysis = False
                self.state.final_result = current_result

                return current_result

            if action == "ESCALATE":

                self.state.status = "ESCALATED"
                self.state.reason = reasoning
                self.state.needs_reanalysis = False
                self.state.final_result = current_result

                return current_result

            self.state.status = "REANALYZING"
            self.state.reason = reasoning
            self.state.needs_reanalysis = True

            previous_reasoning = reasoning
            next_action = action

            print(f"[Vision Agent] Next action: {next_action}")

        self.state.status = "ESCALATED"
        self.state.reason = "Maximum analysis attempts reached."
        self.state.needs_reanalysis = False

        if current_result is None:
            raise RuntimeError(
                "Vision Agent completed without a result."
            )

        self.state.final_result = current_result

        return current_result

    # ========================================================
    # STATE ACCESS
    # ========================================================

    def get_state(self) -> VisionAgentState:
        return self.state
