"""
Quick end-to-end test for Agent 2 — RAG Agent.
Run with: python test_rag_agent.py
"""

import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from dotenv import load_dotenv
load_dotenv()

from agents.vision_agent import VisionAnalysis
from agents.rag_agent import RAGAgent

# ============================================================
# MOCK VISION ANALYSIS (simulates Agent 1 output)
# ============================================================

mock_vision = VisionAnalysis(
    product_category="Accessories",
    product_type="Eyeglasses",
    damage_type=(
        "The temple arm detached at the hinge after two weeks "
        "of normal use; possible latent manufacturing defect"
    ),
    damage_location="Left hinge / temple arm",
    severity="High",
    confidence=0.95,
    visual_evidence=(
        "The left temple arm is detached at the hinge. "
        "The customer reports that it happened after two weeks "
        "of normal use, without an impact."
    ),
    description_consistency="Consistent with the customer's description.",
    uncertainty=(
        "The image shows the detached arm, but cannot by itself prove "
        "that this is a manufacturing defect or confirm the usage history."
    ),
)

# ============================================================
# RUN RAG AGENT
# ============================================================

print("=" * 60)
print("AGENT 2 — POLICY RAG AGENT")
print("=" * 60)
print(f"Product  : {mock_vision.product_type}")
print(f"Damage   : {mock_vision.damage_type}")
print(f"Severity : {mock_vision.severity}")
print()

agent = RAGAgent()
result = agent.retrieve_policy(mock_vision)

# ============================================================
# DISPLAY RESULT
# ============================================================

print()
print("=" * 60)
print("POLICY RESULT")
print("=" * 60)
print(f"Retrieval OK      : {result.retrieval_successful}")
print(f"Applicable policy : {result.applicable_policy}")
print(f"Sources           : {result.sources}")
print(f"Rewritten query   : {result.query}")
print(f"Chunks returned   : {len(result.chunks)}")
print()

print("--- Reranked Chunks ---")
for i, c in enumerate(result.chunks):
    print(f"[{i+1}] {c.doc_type} | score={c.relevance_score:.3f}")
    print(f"    {c.text[:200]}")
    print()

print("--- LLM Synthesis ---")
print(result.summary)

if hasattr(result, "policy_summary") and result.policy_summary:
    ps = result.policy_summary
    print()
    print(f"Policy conditions : {ps.policy_conditions}")
    print(f"Claim assessment  : {ps.claim_assessment}")
    print(f"Exceptions        : {ps.exceptions}")
    print(f"Uncertainty       : {ps.uncertainty}")

print()
print("=" * 60)
print("DONE")
print("=" * 60)
