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
    product_category="Apparel and Accessories",
    product_type="Eyeglasses",
    damage_type="Broken temple arm completely detached at the hinge",
    damage_location="Left hinge / temple arm",
    severity="High",
    confidence=0.97,
    visual_evidence=(
        "Black eyeglasses with left temple arm completely detached "
        "at the hinge. Clean break at the metal joint indicating "
        "structural failure."
    ),
    description_consistency=(
        "Inconsistent — customer described shoes, image shows eyeglasses."
    ),
    uncertainty=(
        "Customer description does not match the visible product."
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
