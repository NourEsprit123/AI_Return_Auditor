"""
End-to-end test for Agent 3 — Decision Agent.
Tests 4 scenarios: approved, guardrail hit, expired window, high value.
Run with: python test_decision_agent.py
"""

import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from dotenv import load_dotenv
load_dotenv()

from agents.vision_agent import VisionAnalysis
from agents.decision_agent import DecisionAgent
from rag.retriever import PolicyResult, RetrievedChunk


# ============================================================
# HELPERS
# ============================================================

def make_policy(applicable: str, summary: str, chunks_text: list[str]) -> PolicyResult:
    chunks = [
        RetrievedChunk(
            text=t,
            source="return_policy.txt",
            doc_type=applicable,
            chunk_id=i,
            relevance_score=0.85 - i * 0.1,
        )
        for i, t in enumerate(chunks_text)
    ]
    r = PolicyResult(
        query="test query",
        chunks=chunks,
        sources=["return_policy.txt"],
        summary=summary,
        applicable_policy=applicable,
        retrieval_successful=True,
    )
    return r


def print_result(label: str, result):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {label}")
    print(f"{'='*60}")
    print(f"Decision      : {result.decision}")
    print(f"Confidence    : {result.confidence:.0%}")
    print(f"Risk          : {result.risk_level}")
    print(f"Guardrail hit : {result.guardrail_hit}")
    print(f"Reason        : {result.reason}")
    print("Evidence chain:")
    for e in result.evidence_chain:
        print(f"  • {e}")
    print(f"\nReasoning:\n{result.reasoning_steps}")


# ============================================================
# SCENARIOS
# ============================================================

agent = DecisionAgent()

# ----------------------------------------------------------
# Scenario 1: Should be APPROVED
# Consistent damage, policy applies, within window, low value
# ----------------------------------------------------------
v1 = VisionAnalysis(
    product_category="Footwear",
    product_type="Running shoes",
    damage_type="Visible stain on left shoe",
    damage_location="Left shoe upper",
    severity="Medium",
    confidence=0.91,
    visual_evidence="Clear stain visible on the left shoe upper, consistent with delivery damage.",
    description_consistency="Consistent — customer described a stain on the left shoe.",
    uncertainty="None",
)
p1 = make_policy(
    "Return Policy",
    "Footwear with visible stains present at delivery is eligible for return within 30 days.",
    [
        "Footwear: returns accepted for visible stains present at delivery.",
        "Products received with visible defects may qualify for return within 30 days.",
    ],
)
o1 = {
    "order_id": "ORD-004",
    "product_name": "Adidas Ultraboost 22",
    "product_category": "Footwear",
    "purchase_price": 180.00,
    "delivery_status": "Delivered",
    "days_since_delivery": 8,
    "return_window_days": 30,
    "within_return_window": True,
    "found": True,
}
r1 = agent.decide(v1, p1, o1)
print_result("SCENARIO 1 — Expected: APPROVED (consistent, in window)", r1)

# ----------------------------------------------------------
# Scenario 2: Guardrail — description inconsistency
# ----------------------------------------------------------
v2 = VisionAnalysis(
    product_category="Apparel and Accessories",
    product_type="Eyeglasses",
    damage_type="Broken temple arm detached at hinge",
    damage_location="Left hinge",
    severity="High",
    confidence=0.97,
    visual_evidence="Eyeglasses with left temple arm completely detached at the hinge.",
    description_consistency="Inconsistent — customer described shoes, image shows eyeglasses.",
    uncertainty="Customer description does not match the visible product.",
)
p2 = make_policy(
    "Return Policy",
    "Accessories with broken components are eligible for return.",
    ["Accessories: returns accepted for broken components present at delivery."],
)
o2 = {
    "order_id": "ORD-003",
    "product_name": "Ray-Ban Wayfarer",
    "product_category": "Accessories",
    "purchase_price": 165.00,
    "delivery_status": "Delivered",
    "days_since_delivery": 3,
    "return_window_days": 30,
    "within_return_window": True,
    "found": True,
}
r2 = agent.decide(v2, p2, o2)
print_result("SCENARIO 2 — Expected: HUMAN_REVIEW (guardrail: description inconsistency)", r2)

# ----------------------------------------------------------
# Scenario 3: Guardrail — return window expired
# ----------------------------------------------------------
v3 = VisionAnalysis(
    product_category="Footwear",
    product_type="Nike Pegasus 41",
    damage_type="Sole separation",
    damage_location="Left shoe sole",
    severity="High",
    confidence=0.88,
    visual_evidence="Left shoe sole partially detached from the upper.",
    description_consistency="Consistent",
    uncertainty="None",
)
p3 = make_policy(
    "Return Policy",
    "Footwear with sole separation is eligible for return.",
    ["Footwear: returns accepted for sole separation."],
)
o3 = {
    "order_id": "ORD-001",
    "product_name": "Nike Pegasus 41",
    "product_category": "Footwear",
    "purchase_price": 120.00,
    "delivery_status": "Delivered",
    "days_since_delivery": 37,
    "return_window_days": 30,
    "within_return_window": False,
    "found": True,
}
r3 = agent.decide(v3, p3, o3)
print_result("SCENARIO 3 — Expected: HUMAN_REVIEW (guardrail: return window expired)", r3)

# ----------------------------------------------------------
# Scenario 4: Guardrail — high value order
# ----------------------------------------------------------
v4 = VisionAnalysis(
    product_category="Electronics",
    product_type="Samsung Galaxy S24",
    damage_type="Cracked screen",
    damage_location="Front display",
    severity="High",
    confidence=0.95,
    visual_evidence="Screen cracked across the entire display surface.",
    description_consistency="Consistent",
    uncertainty="None",
)
p4 = make_policy(
    "Return Policy",
    "Electronics with cracked screens are eligible for return within 30 days.",
    ["Electronics: returns accepted for cracked screens present at delivery."],
)
o4 = {
    "order_id": "ORD-002",
    "product_name": "Samsung Galaxy S24",
    "product_category": "Electronics",
    "purchase_price": 899.00,
    "delivery_status": "Delivered",
    "days_since_delivery": 5,
    "return_window_days": 30,
    "within_return_window": True,
    "found": True,
}
r4 = agent.decide(v4, p4, o4)
print_result("SCENARIO 4 — Expected: HUMAN_REVIEW (guardrail: high value order)", r4)

print("\n" + "="*60)
print("ALL SCENARIOS COMPLETE")
print("="*60)
