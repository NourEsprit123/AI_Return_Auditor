from collections import Counter
from .config import MIN_CONSENSUS_RATIO

def evaluate_consensus(samples: list, item_value: float = 0.0, high_value_limit: float = 500.0) -> dict:
    """
    Analyzes sample outputs via majority voting and applies business guardrails.
    """
    # 1. Filter out malformed or errored samples
    valid_samples = [s for s in samples if "decision" in s and "error" not in s]

    if not valid_samples:
        return {
            "status": "ESCALATED",
            "decision": "ESCALATE_HUMAN",
            "confidence": 0.0,
            "customer_message": "Your case has been forwarded to a Senior Escalations Specialist for specialized review."
        }

    # 2. Guardrail Check: High-Value Override
    if item_value > high_value_limit:
        return {
            "status": "ESCALATED",
            "decision": "ESCALATE_HUMAN",
            "confidence": 1.0,
            "customer_message": "Due to the high value of your item, your request has been routed directly to Sarah from our Senior Escalations Team for verification. Expect an update within 1-2 business hours."
        }

    # 3. Tally Majority Votes
    decisions = [s["decision"] for s in valid_samples]
    vote_counts = Counter(decisions)
    most_common_decision, count = vote_counts.most_common(1)[0]
    agreement_ratio = count / len(decisions)

    # 4. Guardrail Check: Low Consensus or Explicit Escalation
    if agreement_ratio < MIN_CONSENSUS_RATIO or most_common_decision == "ESCALATE_HUMAN":
        return {
            "status": "ESCALATED",
            "decision": "ESCALATE_HUMAN",
            "confidence": agreement_ratio,
            "customer_message": "Your return requires secondary review by a human specialist. Assigned to Sarah (Senior Escalations Team). Reference: #AUD-ESC-9942."
        }

    # 5. Successful Consensus Resolution
    winning_sample = next(s for s in valid_samples if s["decision"] == most_common_decision)

    return {
        "status": "COMPLETED",
        "decision": most_common_decision,
        "confidence": agreement_ratio,
        "customer_message": winning_sample.get("actionable_instructions"),
        "reasoning": winning_sample.get("reasoning_summary")
    }