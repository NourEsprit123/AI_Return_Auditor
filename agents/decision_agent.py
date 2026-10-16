"""
agents/decision_agent.py
------------------------
Agent 3 — Claim Evaluator & Decision Agent

Architecture: Two-layer decision system

  Layer 1 — Python Guardrails (before the LLM)
    Deterministic rules that immediately escalate unsafe cases
    to HUMAN_REVIEW without calling Gemini. Fast, auditable,
    explainable. No LLM involved.

  Layer 2 — LLM Decision (only if all guardrails pass)
    Few-shot + chain-of-thought prompt with Gemini.
    Produces a structured DecisionResult.

Input:
  VisionAnalysis  — structured output from Agent 1
  PolicyResult    — structured output from Agent 2
  order_info      — dict from services/order_service.py

Output:
  DecisionResult  — decision, confidence, risk, reason, evidence chain
"""

import os
import time
from pathlib import Path
from typing import Optional

# Force PyTorch backend before any sentence-transformers import
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from agents.vision_agent import VisionAnalysis
from rag.retriever import PolicyResult


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "decision_agent_v1.txt"


# ============================================================
# CONFIGURATION
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv(
    "GEMINI_DECISION_MODEL",
    "gemini-3.5-flash",
)

MAX_MODEL_RETRIES = 2
RETRY_DELAY_SECONDS = 3

# Guardrail thresholds
MIN_VISION_CONFIDENCE   = 0.60
HIGH_VALUE_THRESHOLD    = 500.0


# ============================================================
# STRUCTURED OUTPUT — DECISION RESULT
# ============================================================

class DecisionResult(BaseModel):
    """
    Final structured output of Agent 3.
    Consumed by the Streamlit Decision view and the n8n workflow.
    """

    decision: str = Field(
        description="Final decision: 'APPROVED' or 'HUMAN_REVIEW'."
    )

    confidence: float = Field(
        description="Overall decision confidence between 0.0 and 1.0.",
        ge=0.0,
        le=1.0,
    )

    risk_level: str = Field(
        description="Risk assessment: 'LOW', 'MEDIUM', or 'HIGH'."
    )

    reason: str = Field(
        description=(
            "2 to 4 sentences explaining the decision, "
            "citing the evidence from Vision and Policy agents."
        )
    )

    guardrail_hit: str = Field(
        description=(
            "Name of the guardrail that triggered the escalation, "
            "or 'None' if the LLM made the decision."
        )
    )

    evidence_chain: list[str] = Field(
        description=(
            "3 to 5 bullet points summarising the evidence used."
        )
    )

    reasoning_steps: str = Field(
        description=(
            "Full 5-step reasoning chain followed by the agent."
        )
    )


# ============================================================
# GUARDRAIL DEFINITIONS
# ============================================================

class GuardrailResult(BaseModel):
    triggered: bool
    name: str
    reason: str
    risk_level: str


def run_guardrails(
    vision: VisionAnalysis,
    policy: PolicyResult,
    order: dict,
) -> Optional[GuardrailResult]:
    """
    Layer 1 — Python guardrails.

    Runs deterministic checks before calling the LLM.
    Returns the first triggered GuardrailResult, or None if all pass.

    Order matters: most critical checks run first.
    """

    # ----------------------------------------------------------
    # G1 — Order not delivered
    # ----------------------------------------------------------
    delivery_status = str(order.get("delivery_status", "")).lower()
    if "delivered" not in delivery_status:
        return GuardrailResult(
            triggered=True,
            name="ORDER_NOT_DELIVERED",
            reason=(
                f"The order status is '{order.get('delivery_status', 'Unknown')}'. "
                "A return can only be processed for delivered orders."
            ),
            risk_level="HIGH",
        )

    # ----------------------------------------------------------
    # G2 — Return window expired
    # ----------------------------------------------------------
    within_window = order.get("within_return_window", True)
    days = order.get("days_since_delivery", -1)

    if within_window is False or (days > 0 and days > order.get("return_window_days", 30)):
        return GuardrailResult(
            triggered=True,
            name="RETURN_WINDOW_EXPIRED",
            reason=(
                f"The return window has expired. "
                f"The order was delivered {days} day(s) ago "
                f"and the return window is {order.get('return_window_days', 30)} days."
            ),
            risk_level="HIGH",
        )

    # ----------------------------------------------------------
    # G3 — Low vision confidence
    # ----------------------------------------------------------
    if vision.confidence < MIN_VISION_CONFIDENCE:
        return GuardrailResult(
            triggered=True,
            name="LOW_VISION_CONFIDENCE",
            reason=(
                f"Vision Agent confidence is {vision.confidence:.0%}, "
                f"below the minimum threshold of {MIN_VISION_CONFIDENCE:.0%}. "
                "The visual evidence is insufficient for an automatic decision."
            ),
            risk_level="MEDIUM",
        )

    # ----------------------------------------------------------
    # G4 — Description inconsistency
    # ----------------------------------------------------------
    consistency = (vision.description_consistency or "").lower()
    is_inconsistent = any(x in consistency for x in [
        "inconsistent", "contradict", "does not match",
        "not match", "unsupported", "mismatch",
    ])

    if is_inconsistent:
        return GuardrailResult(
            triggered=True,
            name="DESCRIPTION_INCONSISTENCY",
            reason=(
                "The customer description does not match the visual evidence. "
                f"Vision Agent reported: '{vision.description_consistency}'. "
                "A human reviewer must verify the correct product and resolve "
                "the inconsistency."
            ),
            risk_level="MEDIUM",
        )

    # ----------------------------------------------------------
    # G5 — No policy retrieved
    # ----------------------------------------------------------
    if not policy.chunks or not policy.retrieval_successful:
        return GuardrailResult(
            triggered=True,
            name="NO_POLICY_FOUND",
            reason=(
                "No applicable return or warranty policy was retrieved "
                "for this product and damage type. A human reviewer must "
                "determine eligibility manually."
            ),
            risk_level="MEDIUM",
        )

    # ----------------------------------------------------------
    # G6 — High value order
    # ----------------------------------------------------------
    price = float(order.get("purchase_price", 0.0))
    if price > HIGH_VALUE_THRESHOLD:
        return GuardrailResult(
            triggered=True,
            name="HIGH_VALUE_ORDER",
            reason=(
                f"The order value is ${price:.2f}, which exceeds the "
                f"${HIGH_VALUE_THRESHOLD:.0f} threshold for automatic approval. "
                "High-value orders require human reviewer verification."
            ),
            risk_level="HIGH",
        )

    # ----------------------------------------------------------
    # G7 — Unknown severity
    # ----------------------------------------------------------
    if (vision.severity or "").lower() in ["unknown", ""]:
        return GuardrailResult(
            triggered=True,
            name="UNKNOWN_DAMAGE_SEVERITY",
            reason=(
                "The Vision Agent could not determine the damage severity. "
                "An automatic decision cannot be made without a severity assessment."
            ),
            risk_level="MEDIUM",
        )

    # All guardrails passed
    return None


# ============================================================
# DECISION AGENT
# ============================================================

class DecisionAgent:
    """
    Claim Evaluator — two-layer decision agent.

    Layer 1: Python guardrails (deterministic, fast, auditable)
    Layer 2: Gemini LLM with few-shot + chain-of-thought prompt
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or API_KEY
        self.model_name = model_name or MODEL_NAME

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=self.api_key)
        self.prompt = self._load_prompt()

        print("[DecisionAgent] Initialized.")

    # --------------------------------------------------------
    # LOAD PROMPT
    # --------------------------------------------------------

    def _load_prompt(self) -> str:

        if not PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Decision Agent prompt not found: {PROMPT_PATH}"
            )

        return PROMPT_PATH.read_text(encoding="utf-8")

    # --------------------------------------------------------
    # GUARDRAIL → DECISION RESULT
    # --------------------------------------------------------

    def _guardrail_to_decision(
        self,
        guardrail: GuardrailResult,
        vision: VisionAnalysis,
        policy: PolicyResult,
        order: dict,
    ) -> DecisionResult:
        """Convert a triggered guardrail into a DecisionResult."""

        evidence = [
            f"Vision: {vision.product_type} — {vision.damage_type} "
            f"({vision.severity} severity, {vision.confidence:.0%} confidence)",
            f"Policy: {policy.applicable_policy or 'Not determined'}",
            f"Order: {order.get('order_id', '?')} — "
            f"{order.get('delivery_status', '?')} — "
            f"${order.get('purchase_price', 0):.2f}",
            f"Guardrail triggered: {guardrail.name}",
        ]

        # Map risk level to confidence
        confidence_map = {"LOW": 0.35, "MEDIUM": 0.25, "HIGH": 0.15}
        confidence = confidence_map.get(guardrail.risk_level, 0.20)

        return DecisionResult(
            decision="HUMAN_REVIEW",
            confidence=confidence,
            risk_level=guardrail.risk_level,
            reason=guardrail.reason,
            guardrail_hit=guardrail.name,
            evidence_chain=evidence,
            reasoning_steps=(
                f"Step 1 — Vision reviewed.\n"
                f"Step 2 — Policy reviewed.\n"
                f"Step 3 — Order reviewed.\n"
                f"Step 4 — Guardrail '{guardrail.name}' triggered. "
                f"Reason: {guardrail.reason}\n"
                f"Step 5 — Decision: HUMAN_REVIEW (guardrail escalation)."
            ),
        )

    # --------------------------------------------------------
    # LLM DECISION
    # --------------------------------------------------------

    def _llm_decide(
        self,
        vision: VisionAnalysis,
        policy: PolicyResult,
        order: dict,
    ) -> DecisionResult:
        """
        Layer 2 — LLM decision.
        Called only when all guardrails pass.
        """

        # Build policy chunks text
        chunks_text = "\n".join(
            f"  [{i+1}] {c.doc_type}: {c.text[:300]}"
            for i, c in enumerate(policy.chunks)
        ) if policy.chunks else "  No chunks retrieved."

        decision_prompt = f"""
{self.prompt}

============================================================
CLAIM TO EVALUATE
============================================================

--- VISION AGENT OUTPUT (Agent 1) ---
product_category        : {vision.product_category}
product_type            : {vision.product_type}
damage_type             : {vision.damage_type}
damage_location         : {vision.damage_location}
severity                : {vision.severity}
confidence              : {vision.confidence:.0%}
visual_evidence         : {vision.visual_evidence}
description_consistency : {vision.description_consistency}
uncertainty             : {vision.uncertainty}

--- POLICY RAG OUTPUT (Agent 2) ---
applicable_policy  : {policy.applicable_policy}
retrieval_query    : {policy.query}
sources            : {', '.join(policy.sources) if policy.sources else 'None'}
policy_summary     : {policy.summary}

Retrieved chunks:
{chunks_text}

--- ORDER INFORMATION ---
order_id             : {order.get('order_id', 'Unknown')}
product_name         : {order.get('product_name', 'Unknown')}
product_category     : {order.get('product_category', 'Unknown')}
purchase_price       : ${order.get('purchase_price', 0.0):.2f}
delivery_status      : {order.get('delivery_status', 'Unknown')}
days_since_delivery  : {order.get('days_since_delivery', 'Unknown')}
return_window_days   : {order.get('return_window_days', 30)}
within_return_window : {order.get('within_return_window', 'Unknown')}

============================================================
INSTRUCTIONS
============================================================

Follow the 5-step reasoning chain from the examples above.
Return only the structured DecisionResult.
"""

        models_to_try = [
            self.model_name,
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.1-flash-lite",
        ]
        models_to_try = list(dict.fromkeys(models_to_try))

        for model_name in models_to_try:

            retry_count = 0

            while retry_count <= MAX_MODEL_RETRIES:

                try:

                    print(f"[DecisionAgent] LLM decision | Model: {model_name}")

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=decision_prompt,
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": DecisionResult,
                        },
                    )

                    if getattr(response, "parsed", None):
                        return response.parsed

                    if getattr(response, "text", None):
                        return DecisionResult.model_validate_json(
                            response.text
                        )

                    raise RuntimeError("Empty response from LLM.")

                except Exception as exc:

                    error_text = str(exc).lower()
                    is_temporary = any(x in error_text for x in [
                        "503", "unavailable", "429",
                        "rate limit", "overloaded", "high demand",
                    ])

                    if is_temporary and retry_count < MAX_MODEL_RETRIES:
                        retry_count += 1
                        print(
                            f"[DecisionAgent] Temporary error. "
                            f"Retry {retry_count}/{MAX_MODEL_RETRIES} in {RETRY_DELAY_SECONDS}s..."
                        )
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue

                    print(f"[DecisionAgent] Model {model_name} failed: {exc}")
                    break

        # All models failed — safe fallback
        return self._fallback_decision(vision, policy, order)

    # --------------------------------------------------------
    # FALLBACK DECISION
    # --------------------------------------------------------

    def _fallback_decision(
        self,
        vision: VisionAnalysis,
        policy: PolicyResult,
        order: dict,
    ) -> DecisionResult:
        """Safe fallback when LLM is unavailable."""

        return DecisionResult(
            decision="HUMAN_REVIEW",
            confidence=0.10,
            risk_level="HIGH",
            reason=(
                "The decision LLM was unavailable. "
                "The claim has been automatically escalated for human review. "
                "All evidence is available for the reviewer."
            ),
            guardrail_hit="LLM_UNAVAILABLE",
            evidence_chain=[
                f"Vision: {vision.product_type} — {vision.damage_type}",
                f"Policy: {policy.applicable_policy or 'Unknown'}",
                f"Order: {order.get('order_id', '?')}",
                "LLM synthesis failed — human review required.",
            ],
            reasoning_steps=(
                "LLM unavailable. Automatic escalation to human review."
            ),
        )

    # --------------------------------------------------------
    # MAIN ENTRY POINT
    # --------------------------------------------------------

    def decide(
        self,
        vision: VisionAnalysis,
        policy: PolicyResult,
        order: dict,
    ) -> DecisionResult:
        """
        Full two-layer decision pipeline.

        Parameters
        ----------
        vision : VisionAnalysis from Agent 1.
        policy : PolicyResult from Agent 2.
        order  : Order info dict from OrderService.

        Returns
        -------
        DecisionResult with decision, confidence, risk, reason, evidence.
        """

        print(
            f"\n[DecisionAgent] Evaluating claim: "
            f"{vision.product_type} / {vision.damage_type}"
        )

        # --------------------------------------------------
        # LAYER 1 — Guardrails
        # --------------------------------------------------

        guardrail = run_guardrails(vision, policy, order)

        if guardrail:
            print(
                f"[DecisionAgent] Guardrail triggered: {guardrail.name}"
            )
            return self._guardrail_to_decision(guardrail, vision, policy, order)

        print("[DecisionAgent] All guardrails passed. Calling LLM...")

        # --------------------------------------------------
        # LAYER 2 — LLM Decision
        # --------------------------------------------------

        result = self._llm_decide(vision, policy, order)

        print(
            f"[DecisionAgent] Decision: {result.decision} "
            f"({result.confidence:.0%} confidence, {result.risk_level} risk)"
        )

        return result
