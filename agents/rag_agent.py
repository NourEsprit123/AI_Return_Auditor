"""
agents/rag_agent.py
-------------------
Agent 2 — Policy RAG Agent

Implements the full Modular RAG pipeline for policy retrieval:

  Module 1 — Query Rewriting   (LLM prompt — this file)
  Module 2 — Dense Retrieval   (rag/retriever.py → ChromaDB)
  Module 3 — Reranking         (rag/retriever.py → cross-encoder)
  Module 4 — Compression       (rag/retriever.py → sentence filter)
  Module 5 — LLM Synthesis     (Gemini → structured PolicyResult)

Input:  VisionAnalysis (from Agent 1)
Output: PolicyResult  (consumed by Agent 3)

Architecture: Modular RAG
  Each module is independently justified and replaceable.
  See RAG_DESIGN.md for the full architecture justification.
"""

import os
import time
from pathlib import Path
from typing import Optional

# Force PyTorch backend before sentence-transformers loads
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from agents.vision_agent import VisionAnalysis
from rag.retriever import (
    ModularRAGRetriever,
    PolicyResult,
    RetrievedChunk,
    setup_retriever,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "rag_agent_v1.txt"


# ============================================================
# CONFIGURATION
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv(
    "GEMINI_RAG_MODEL",
    "gemini-2.0-flash-lite",
)

MAX_MODEL_RETRIES = 2
RETRY_DELAY_SECONDS = 3


# ============================================================
# STRUCTURED LLM OUTPUT — POLICY SUMMARY
# ============================================================

class PolicySummary(BaseModel):
    """
    Structured output of the LLM synthesis step (Module 5).
    Produced by Gemini after reading the retrieved chunks.
    """

    applicable_policy: str = Field(
        description=(
            "The name of the most relevant policy: "
            "'Return Policy', 'Refund Policy', or 'Warranty Policy'."
        )
    )

    policy_conditions: str = Field(
        description=(
            "The specific conditions from the retrieved policy "
            "that are relevant to this claim."
        )
    )

    claim_assessment: str = Field(
        description=(
            "Whether the described claim appears to satisfy "
            "the retrieved policy conditions. "
            "Do NOT make an approval/rejection decision."
        )
    )

    exceptions: str = Field(
        description=(
            "Any exceptions, special conditions, or return window "
            "requirements noted in the retrieved chunks."
        )
    )

    uncertainty: str = Field(
        description=(
            "Anything the retrieved chunks do not clearly address "
            "about this specific claim."
        )
    )

    synthesis: str = Field(
        description=(
            "Full 3 to 6 sentence policy summary grounded "
            "in the retrieved chunks."
        )
    )


# ============================================================
# RAG AGENT
# ============================================================

class RAGAgent:
    """
    Policy Retrieval Agent — Modular RAG implementation.

    Workflow:
      1. Rewrite the search query using a prompt and the VisionAnalysis fields.
      2. Retrieve top-5 candidate chunks from ChromaDB (dense retrieval).
      3. Rerank top-5 → top-3 using a cross-encoder.
      4. Apply context compression to each chunk.
      5. Synthesize the retrieved chunks into a structured PolicySummary
         using Gemini + a chain-of-thought prompt.
      6. Return a PolicyResult for Agent 3.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        retriever: Optional[ModularRAGRetriever] = None,
    ):

        self.api_key = api_key or API_KEY
        self.model_name = model_name or MODEL_NAME

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=self.api_key)
        self.prompt = self._load_prompt()

        # Initialize retriever (builds index on first run if needed)
        self.retriever = retriever or setup_retriever()

        print("[RAGAgent] Initialized.")

    # --------------------------------------------------------
    # LOAD PROMPT
    # --------------------------------------------------------

    def _load_prompt(self) -> str:

        if not PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"RAG Agent prompt not found: {PROMPT_PATH}"
            )

        return PROMPT_PATH.read_text(encoding="utf-8")

    # --------------------------------------------------------
    # MODULE 1 — QUERY REWRITING
    # --------------------------------------------------------

    def _rewrite_query(self, vision: VisionAnalysis) -> str:
        """
        Module 1 — Query Rewriting.

        Transforms the structured VisionAnalysis into an optimized
        search query using policy-oriented terminology.

        Uses the Gemini LLM to produce a query that is more likely
        to match the terminology used in policy documents than the
        raw customer description.
        """

        rewrite_prompt = f"""
{self.prompt}

============================================================
QUERY REWRITING TASK
============================================================

Produce a precise policy search query from the following damage analysis.
Output only the search query. No explanation. No label. One or two sentences.

damage_type             : {vision.damage_type}
product_type            : {vision.product_type}
product_category        : {vision.product_category}
severity                : {vision.severity}
description_consistency : {vision.description_consistency}
visual_evidence         : {vision.visual_evidence}
"""

        try:

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=rewrite_prompt,
            )

            query = (response.text or "").strip()

            if not query:
                raise ValueError("Empty query rewrite response.")

            print(f"[RAGAgent] Rewritten query: {query}")

            return query

        except Exception as exc:

            # Fallback: build a simple deterministic query from fields
            fallback = (
                f"Return and refund policy for {vision.product_type} "
                f"with {vision.damage_type}, {vision.severity} severity"
            )

            print(
                f"[RAGAgent] Query rewrite failed ({exc}). "
                f"Using fallback: {fallback}"
            )

            return fallback

    # --------------------------------------------------------
    # MODULE 5 — LLM SYNTHESIS
    # --------------------------------------------------------

    def _synthesize(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        vision: VisionAnalysis,
    ) -> PolicySummary:
        """
        Module 5 — LLM Synthesis.

        Sends the retrieved (and compressed) chunks to Gemini with
        a chain-of-thought prompt. Returns a structured PolicySummary.
        """

        chunks_text = "\n\n".join(
            f"[Chunk {i+1} — {c.doc_type} | source: {c.source} "
            f"| relevance: {c.relevance_score:.2f}]\n{c.text}"
            for i, c in enumerate(chunks)
        )

        synthesis_prompt = f"""
{self.prompt}

============================================================
POLICY SYNTHESIS TASK
============================================================

Search query used for retrieval:
{query}

Damage analysis from Vision Agent:
  product_type            : {vision.product_type}
  product_category        : {vision.product_category}
  damage_type             : {vision.damage_type}
  damage_location         : {vision.damage_location}
  severity                : {vision.severity}
  confidence              : {vision.confidence:.0%}
  description_consistency : {vision.description_consistency}
  uncertainty             : {vision.uncertainty}

Retrieved policy chunks:
{chunks_text}

============================================================
INSTRUCTIONS
============================================================

Follow the 5-step reasoning chain in the prompt.
Return only the structured PolicySummary result.
Do NOT approve or reject the claim.
"""

        models_to_try = [
            self.model_name,
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]

        models_to_try = list(dict.fromkeys(models_to_try))

        for model_name in models_to_try:

            retry_count = 0

            while retry_count <= MAX_MODEL_RETRIES:

                try:

                    print(
                        f"[RAGAgent] Synthesis | Model: {model_name}"
                    )

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=synthesis_prompt,
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": PolicySummary,
                        },
                    )

                    if getattr(response, "parsed", None):
                        return response.parsed

                    if getattr(response, "text", None):
                        return PolicySummary.model_validate_json(
                            response.text
                        )

                    raise RuntimeError("Empty synthesis response.")

                except Exception as exc:

                    error_text = str(exc).lower()

                    is_temporary = any(
                        x in error_text
                        for x in [
                            "503", "unavailable", "429",
                            "rate limit", "overloaded",
                        ]
                    )

                    if is_temporary and retry_count < MAX_MODEL_RETRIES:
                        retry_count += 1
                        print(
                            f"[RAGAgent] Temporary error. "
                            f"Retry {retry_count}/{MAX_MODEL_RETRIES}..."
                        )
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue

                    print(
                        f"[RAGAgent] Model {model_name} failed: {exc}"
                    )
                    break

        # All models failed — return a fallback summary
        return self._fallback_summary(chunks)

    # --------------------------------------------------------
    # FALLBACK SUMMARY
    # --------------------------------------------------------

    def _fallback_summary(
        self,
        chunks: list[RetrievedChunk],
    ) -> PolicySummary:
        """
        Deterministic fallback when LLM synthesis fails.
        Builds a basic summary directly from the chunk metadata.
        """

        sources = list({c.doc_type for c in chunks})

        return PolicySummary(
            applicable_policy=sources[0] if sources else "Unknown",
            policy_conditions=(
                "Policy conditions could not be synthesized "
                "due to an LLM error. See retrieved chunks."
            ),
            claim_assessment=(
                "Assessment unavailable. Human review recommended."
            ),
            exceptions="Not determined due to synthesis failure.",
            uncertainty=(
                "LLM synthesis failed. Retrieval succeeded. "
                "Chunks are available for manual review."
            ),
            synthesis=(
                "The RAG synthesis step encountered an error. "
                f"{len(chunks)} policy chunk(s) were retrieved from: "
                f"{', '.join(sources) if sources else 'unknown sources'}. "
                "Human review is recommended."
            ),
        )

    # --------------------------------------------------------
    # MAIN ENTRY POINT
    # --------------------------------------------------------

    def retrieve_policy(
        self,
        vision: VisionAnalysis,
    ) -> PolicyResult:
        """
        Full Modular RAG pipeline.

        Parameters
        ----------
        vision : VisionAnalysis output from Agent 1.

        Returns
        -------
        PolicyResult containing retrieved chunks and LLM synthesis.
        Consumed by Agent 3 (Decision Agent).
        """

        print(
            f"\n[RAGAgent] Starting policy retrieval for: "
            f"{vision.product_type} / {vision.damage_type}"
        )

        # --------------------------------------------------
        # MODULE 1 — Query Rewriting
        # --------------------------------------------------

        query = self._rewrite_query(vision)

        # --------------------------------------------------
        # MODULES 2, 3, 4 — Dense Retrieval + Reranking + Compression
        # --------------------------------------------------

        try:

            chunks = self.retriever.retrieve(
                query=query,
                compress=True,
            )

        except Exception as exc:

            print(f"[RAGAgent] Retrieval failed: {exc}")

            return PolicyResult(
                query=query,
                chunks=[],
                sources=[],
                summary="Retrieval failed. Human review required.",
                applicable_policy="Unknown",
                retrieval_successful=False,
                error=str(exc),
            )

        if not chunks:

            print("[RAGAgent] No chunks retrieved.")

            return PolicyResult(
                query=query,
                chunks=[],
                sources=[],
                summary=(
                    "No relevant policy was found for this claim. "
                    "Human review required."
                ),
                applicable_policy="Unknown",
                retrieval_successful=False,
                error="No chunks retrieved from knowledge base.",
            )

        print(
            f"[RAGAgent] Retrieved {len(chunks)} chunk(s). "
            "Running LLM synthesis..."
        )

        # --------------------------------------------------
        # MODULE 5 — LLM Synthesis
        # --------------------------------------------------

        summary_obj = self._synthesize(
            query=query,
            chunks=chunks,
            vision=vision,
        )

        unique_sources = list({c.source for c in chunks})

        result = PolicyResult(
            query=query,
            chunks=chunks,
            sources=unique_sources,
            summary=summary_obj.synthesis,
            applicable_policy=summary_obj.applicable_policy,
            retrieval_successful=True,
        )

        # Attach the full synthesis object for the UI
        result.policy_summary = summary_obj

        print(
            f"[RAGAgent] Policy retrieval complete. "
            f"Applicable: {summary_obj.applicable_policy}"
        )

        return result
