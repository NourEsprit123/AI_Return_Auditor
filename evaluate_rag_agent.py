"""Evaluate Agent 2 retrieval and policy synthesis with an LLM judge.

Run from the project root with:
    python evaluate_rag_agent.py
"""

import argparse
import json
import os
import statistics
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from agents.rag_agent import RAGAgent
from agents.vision_agent import VisionAnalysis


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "data" / "knowledge_base"
POLICY_FILES = (
    "return_policy.txt",
    "refund_policy.txt",
    "warranty_policy.txt",
)


class RAGJudgeScore(BaseModel):
    policy_selection: int = Field(ge=0, le=2)
    factual_accuracy: int = Field(ge=0, le=2)
    source_grounding: int = Field(ge=0, le=2)
    completeness: int = Field(ge=0, le=2)
    uncertainty_handling: int = Field(ge=0, le=2)
    rationale: str


JUDGE_INSTRUCTIONS = """
You are evaluating a policy RAG agent. Treat the supplied policy documents
as the only source of truth; do not use outside knowledge.

Score each criterion from 0 to 2:
- policy_selection: 0 wrong policy, 1 partly right/multiple policies without
  prioritization, 2 the best applicable policy is clearly identified.
- factual_accuracy: 0 contains a material contradiction or invented rule,
  1 mostly correct with a minor error, 2 all material claims match the policies.
- source_grounding: 0 important claims are unsupported, 1 some claims are
  supported, 2 the claims are supported by the supplied policy text.
- completeness: 0 misses most required checks, 1 includes some, 2 covers the
  case-specific reference checks.
- uncertainty_handling: 0 asserts unsupported facts or eligibility, 1 notes
  some missing facts, 2 clearly identifies unknown facts and avoids deciding
  approval/refusal when evidence is insufficient.

Grade the agent's output, not the quality of the test case. Use the reference
checks to judge completeness, but cite only information found in the policy
documents. Do not assume dates, cause, delivery condition, or warranty status
unless provided in the case.
"""


TEST_CASES = [
    {
        "id": "eyeglasses-delivery-damage",
        "description": "Eyeglasses with a detached temple arm at delivery",
        "expected_policy": "Return Policy",
        "expected_sources": ["return_policy.txt"],
        "reference_checks": [
            "Accessories including eyeglasses can be returned when a temple arm is broken or detached upon delivery.",
            "A return request must be within 30 days of confirmed delivery and include an order ID, issue description, and photographic evidence.",
            "The customer description conflicts with the eyeglasses visible in the photo, so the case must be escalated for human review.",
            "The image alone does not prove when or how the damage occurred.",
        ],
        "vision": {
            "product_category": "Accessories",
            "product_type": "Eyeglasses",
            "damage_type": "Broken temple arm completely detached at the hinge",
            "damage_location": "Left hinge / temple arm",
            "severity": "High",
            "confidence": 0.97,
            "visual_evidence": "The left temple arm is visibly detached at the hinge.",
            "description_consistency": "Inconsistent: customer described shoes, image shows eyeglasses.",
            "uncertainty": "The image cannot establish whether the damage occurred before delivery.",
        },
    },
    {
        "id": "latent-eyeglasses-defect",
        "description": "Eyeglass hinge failure after two weeks of normal use",
        "expected_policy": "Warranty Policy",
        "expected_sources": ["warranty_policy.txt"],
        "reference_checks": [
            "The warranty policy explicitly gives an eyeglass hinge breaking after two weeks of normal use as an example of a latent defect.",
            "A warranty claim must be within the applicable warranty period and the defect must be a manufacturing defect, not accidental or customer-caused damage.",
            "The customer must submit the claim as a warranty claim and provide evidence of normal use and how the defect was discovered.",
            "Do not infer that every warranty lasts 30 days from purchase: manufacturer durations vary; the policy gives accessories a typical 90-day manufacturer warranty and directs claims beyond 30 days to the manufacturer.",
            "The reported two weeks of normal use and image do not independently prove manufacturing cause or the applicable warranty status.",
        ],
        "vision": {
            "product_category": "Accessories",
            "product_type": "Eyeglasses",
            "damage_type": "Temple arm detached at hinge after two weeks of normal use; possible latent manufacturing defect",
            "damage_location": "Left hinge / temple arm",
            "severity": "High",
            "confidence": 0.95,
            "visual_evidence": "The left temple arm is detached at the hinge.",
            "description_consistency": "Consistent with the customer's description.",
            "uncertainty": "The image cannot prove manufacturing cause or warranty status.",
        },
    },
    {
        "id": "shoes-cosmetic-stain",
        "description": "Shoes arrived with visible cosmetic stains",
        "expected_policy": "Return Policy",
        "expected_sources": ["return_policy.txt", "refund_policy.txt"],
        "reference_checks": [
            "Visible stains present at delivery are an eligible return damage type.",
            "Footwear with signs of outdoor use is not returnable for cosmetic grounds unless the damage was present before first use.",
            "A surface stain that does not affect function may qualify for a partial refund if the customer keeps the item.",
            "The applicable refund amount is not guaranteed; the policy associates percentages with severity.",
            "Do not assert outdoor use or first-use timing unless the case provides that evidence.",
        ],
        "vision": {
            "product_category": "Footwear",
            "product_type": "Running shoes",
            "damage_type": "Visible mud and dirt stains",
            "damage_location": "Upper fabric and midsoles",
            "severity": "Medium",
            "confidence": 0.93,
            "visual_evidence": "Brown stains are visible on the fabric and midsoles.",
            "description_consistency": "Consistent with the customer's description.",
            "uncertainty": "The image cannot establish whether the shoes were used outdoors before the stains appeared.",
        },
    },
    {
        "id": "broken-product-full-refund",
        "description": "Product arrived broken and completely unusable",
        "expected_policy": "Refund Policy",
        "expected_sources": ["refund_policy.txt", "return_policy.txt"],
        "reference_checks": [
            "The refund policy allows a full refund for damage that makes the product completely unusable or unsafe.",
            "The return policy treats broken or cracked components present at delivery as eligible damage.",
            "Refund issuance generally follows return approval and warehouse receipt/inspection unless a stated no-return exception applies.",
            "Do not promise a refund without confirming applicable return and inspection requirements.",
        ],
        "vision": {
            "product_category": "Home and Kitchen",
            "product_type": "Ceramic vase",
            "damage_type": "Broken into several pieces",
            "damage_location": "Main body of the vase",
            "severity": "High",
            "confidence": 0.96,
            "visual_evidence": "The vase body is visibly broken into several pieces.",
            "description_consistency": "Consistent with the customer's description.",
            "uncertainty": "The image cannot verify delivery timing or warehouse inspection.",
        },
    },
]


def load_policy_sources() -> dict[str, str]:
    policies = {}
    for filename in POLICY_FILES:
        path = KNOWLEDGE_BASE_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Policy source is missing: {path}")
        policies[filename] = path.read_text(encoding="utf-8")
    return policies


def score_case(
    client: genai.Client,
    judge_model: str,
    case: dict,
    result,
    policy_sources: dict[str, str],
) -> dict:
    synthesis = getattr(result, "policy_summary", None)
    synthesis_data = (
        synthesis.model_dump(mode="json")
        if synthesis is not None
        else {"synthesis": result.summary, "applicable_policy": result.applicable_policy}
    )
    retrieved_chunks = [
        {
            "source": chunk.source,
            "doc_type": chunk.doc_type,
            "text": chunk.text,
            "relevance_score": chunk.relevance_score,
        }
        for chunk in result.chunks
    ]

    prompt = f"""
{JUDGE_INSTRUCTIONS}

TEST CASE:
{json.dumps({key: value for key, value in case.items() if key != "vision"}, ensure_ascii=False, indent=2)}

FIXED VISION AGENT INPUT:
{json.dumps(case["vision"], ensure_ascii=False, indent=2)}

OFFICIAL POLICY DOCUMENTS:
{json.dumps(policy_sources, ensure_ascii=False, indent=2)}

AGENT 2 RETRIEVED CHUNKS:
{json.dumps(retrieved_chunks, ensure_ascii=False, indent=2)}

AGENT 2 OUTPUT:
{json.dumps({
    "retrieval_successful": result.retrieval_successful,
    "applicable_policy": result.applicable_policy,
    "sources": result.sources,
    "query": result.query,
    "summary": result.summary,
    "policy_summary": synthesis_data,
    "error": result.error,
}, ensure_ascii=False, indent=2)}

Return scores and concise evidence-based rationale.
"""
    response = client.models.generate_content(
        model=judge_model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": RAGJudgeScore,
        },
    )
    if not response.text:
        raise RuntimeError("LLM judge returned an empty response.")
    score = RAGJudgeScore.model_validate_json(response.text)
    score_data = score.model_dump(mode="json")
    score_data["score_out_of_10"] = sum(
        score_data[field]
        for field in (
            "policy_selection",
            "factual_accuracy",
            "source_grounding",
            "completeness",
            "uncertainty_handling",
        )
    )
    return score_data


def summarize(results: list[dict]) -> dict:
    successful = [entry for entry in results if entry["status"] == "success"]
    judged = [entry for entry in successful if entry["judge_score"] is not None]
    judge_fields = (
        "policy_selection",
        "factual_accuracy",
        "source_grounding",
        "completeness",
        "uncertainty_handling",
        "score_out_of_10",
    )
    judge_averages = {
        field: round(statistics.mean(item["judge_score"][field] for item in judged), 2)
        for field in judge_fields
    } if judged else {}

    expected_source_recall = []
    policy_match_count = 0
    for item in successful:
        expected = item["expected_sources"]
        retrieved = set(item["sources"])
        expected_source_recall.append(
            len(set(expected) & retrieved) / len(set(expected))
        )
        if item["applicable_policy"] == item["expected_policy"]:
            policy_match_count += 1

    return {
        "cases": len(results),
        "agent_success_rate": round(len(successful) / len(results), 3) if results else 0,
        "retrieval_success_rate": round(
            sum(item["retrieval_successful"] for item in successful) / len(successful),
            3,
        ) if successful else None,
        "expected_source_recall_mean": round(
            statistics.mean(expected_source_recall), 3
        ) if expected_source_recall else None,
        "applicable_policy_accuracy": round(
            policy_match_count / len(successful), 3
        ) if successful else None,
        "judge_successful_cases": len(judged),
        "judge_average_scores": judge_averages,
        "note": (
            "LLM judge scores are automated estimates. Manually verify the "
            "rationale and source text, especially for policy-critical claims."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Agent 2 retrieval and policy synthesis."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("rag_evaluation_results.json"),
        help="Report path (default: rag_evaluation_results.json)",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Gemini judge model (defaults to GEMINI_JUDGE_MODEL or gemini-3.8-flash)",
    )
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is not configured in the environment or .env file.")

    judge_model = (
        args.judge_model
        or os.getenv("GEMINI_JUDGE_MODEL")
        or "gemini-3.8-flash"
    )
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    policies = load_policy_sources()
    agent = RAGAgent()
    results = []

    for case in TEST_CASES:
        print(f"\nEvaluating {case['id']}: {case['description']}")
        entry = {
            "id": case["id"],
            "description": case["description"],
            "expected_policy": case["expected_policy"],
            "expected_sources": case["expected_sources"],
            "status": "error",
            "retrieval_successful": False,
            "applicable_policy": "Unknown",
            "sources": [],
            "query": "",
            "summary": "",
            "policy_summary": None,
            "retrieved_chunks": [],
            "judge_score": None,
            "errors": [],
        }

        try:
            vision = VisionAnalysis.model_validate(case["vision"])
            rag_result = agent.retrieve_policy(vision)
            entry.update(
                {
                    "status": "success",
                    "retrieval_successful": rag_result.retrieval_successful,
                    "applicable_policy": rag_result.applicable_policy,
                    "sources": rag_result.sources,
                    "query": rag_result.query,
                    "summary": rag_result.summary,
                    "policy_summary": (
                        rag_result.policy_summary.model_dump(mode="json")
                        if getattr(rag_result, "policy_summary", None)
                        else None
                    ),
                    "retrieved_chunks": [
                        {
                            "source": chunk.source,
                            "doc_type": chunk.doc_type,
                            "text": chunk.text,
                            "relevance_score": chunk.relevance_score,
                        }
                        for chunk in rag_result.chunks
                    ],
                }
            )
            entry["expected_sources"] = case["expected_sources"]
            entry["judge_score"] = score_case(
                client=client,
                judge_model=judge_model,
                case=case,
                result=rag_result,
                policy_sources=policies,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            entry["errors"].append(error)
            print(f"  Evaluation failed: {error}")

        results.append(entry)

    report = {
        "judge_model": judge_model,
        "score_scale": "0-2 per criterion; total 0-10",
        "criteria": [
            "policy_selection",
            "factual_accuracy",
            "source_grounding",
            "completeness",
            "uncertainty_handling",
        ],
        "summary": summarize(results),
        "results": results,
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\nEvaluation summary:")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Detailed report: {output_path}")


if __name__ == "__main__":
    main()
