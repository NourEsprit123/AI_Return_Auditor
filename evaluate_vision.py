"""Evaluate the Vision Agent with a Gemini LLM judge.

Input CSV columns: image_path, customer_description
Image paths may be absolute or relative to the CSV file.
"""

import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from PIL import Image
from pydantic import BaseModel, Field

from agents.vision_agent import VisionAgent, VisionAnalysis


class VisionJudgeScore(BaseModel):
    visual_grounding: int = Field(ge=1, le=5)
    damage_identification: int = Field(ge=1, le=5)
    severity_assessment: int = Field(ge=1, le=5)
    description_consistency: int = Field(ge=1, le=5)
    uncertainty_handling: int = Field(ge=1, le=5)
    overall_score: int = Field(ge=1, le=5)
    rationale: str


JUDGE_INSTRUCTIONS = """
You are an independent evaluator of a product-damage vision analysis.
Inspect the supplied image and customer description, then evaluate the
agent's structured analysis. Do not decide return eligibility or apply
return policy.

Score each dimension from 1 (very poor) to 5 (excellent):
- visual_grounding: statements match visible evidence; no invented details.
- damage_identification: damage type and location are appropriately identified.
- severity_assessment: severity matches the visible damage.
- description_consistency: comparison with the customer's claim is accurate.
- uncertainty_handling: ambiguity is acknowledged rather than guessed.
- overall_score: holistic quality, considering the criteria above.

Be conservative. Do not reward confident wording unless the image supports it.
Explain the main reason for the scores briefly.
"""

JUDGE_RETRIES = 2
JUDGE_RETRY_DELAY_SECONDS = 3

COMPLETENESS_FIELDS = tuple(VisionAnalysis.model_fields)
STABILITY_FIELDS = (
    "product_category",
    "product_type",
    "damage_type",
    "damage_location",
    "severity",
    "description_consistency",
)
REFERENCE_FIELDS = (
    "expected_damage_class",
    "expected_severity",
    "expected_description_consistency",
)
DAMAGE_CLASSES = (
    "none",
    "stain",
    "tear",
    "crack",
    "broken",
    "missing_part",
    "other",
    "unknown",
)
SEVERITIES = ("None", "Low", "Medium", "High", "Unknown")
CONSISTENCY_LABELS = ("consistent", "inconsistent", "uncertain")
ORDINAL_SEVERITIES = ("None", "Low", "Medium", "High")


def percentile(values: list[float], percentile_value: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, (len(ordered) * percentile_value + 99) // 100 - 1)
    return round(ordered[index], 3)


def is_complete(analysis: dict) -> bool:
    return all(
        analysis.get(field) is not None
        and (
            not isinstance(analysis[field], str)
            or bool(analysis[field].strip())
        )
        for field in COMPLETENESS_FIELDS
    )


def stability_metrics(outputs: list[dict]) -> dict:
    if len(outputs) < 2:
        return {
            "pairwise_agreement": None,
            "exact_output_pairwise_agreement": None,
            "field_agreement": {field: None for field in STABILITY_FIELDS},
            "confidence_standard_deviation": None,
        }

    pairs = [
        (outputs[left], outputs[right])
        for left in range(len(outputs))
        for right in range(left + 1, len(outputs))
    ]
    field_agreement = {
        field: round(
            sum(first[field] == second[field] for first, second in pairs)
            / len(pairs),
            3,
        )
        for field in STABILITY_FIELDS
    }
    confidences = [output["confidence"] for output in outputs]
    exact_output_agreement = sum(
        all(first[field] == second[field] for field in STABILITY_FIELDS)
        for first, second in pairs
    ) / len(pairs)
    return {
        "pairwise_agreement": round(
            statistics.mean(field_agreement.values()),
            3,
        ),
        "exact_output_pairwise_agreement": round(exact_output_agreement, 3),
        "field_agreement": field_agreement,
        "confidence_standard_deviation": round(
            statistics.pstdev(confidences), 4
        ),
    }


def predict_damage_class(damage_type: str) -> str:
    text = damage_type.casefold()
    if not text.strip() or any(
        term in text for term in ("unknown", "uncertain", "cannot determine", "unable to")
    ):
        return "unknown"
    if any(term in text for term in ("missing", "absent", "detached", "lost part")):
        return "missing_part"
    if any(term in text for term in ("tear", "torn", "ripped", "rip", "hole", "cut")):
        return "tear"
    if any(term in text for term in ("crack", "cracked", "fracture", "shattered")):
        return "crack"
    if any(term in text for term in ("broken", "break", "smashed")):
        return "broken"
    if any(term in text for term in ("stain", "stained", "mud", "dirty", "dirt", "discolor")):
        return "stain"
    if any(
        term in text
        for term in ("none", "no damage", "no visible damage", "no visible defect", "intact")
    ):
        return "none"
    return "other"


def predict_consistency_label(value: str) -> str:
    text = value.strip().casefold()
    inconsistency_indicators = (
        "inconsistent",
        "not consistent",
        "mismatch",
        "discrepancy",
        "does not match",
        "doesn't match",
        "does not correspond",
        "doesn't correspond",
        "not supported by",
        "instead of",
        "rather than",
        "conflicts with",
    )
    if any(indicator in text for indicator in inconsistency_indicators):
        return "inconsistent"
    if text.startswith(("consistent", "matches", "consistent with")):
        return "consistent"
    return "uncertain"


def classification_metrics(expected: list[str], predicted: list[str]) -> dict:
    labels = sorted(set(expected) | set(predicted))
    confusion = {
        label: {predicted_label: 0 for predicted_label in labels}
        for label in labels
    }
    for expected_label, predicted_label in zip(expected, predicted):
        confusion[expected_label][predicted_label] += 1

    per_class = {}
    for label in labels:
        true_positive = confusion[label][label]
        false_positive = sum(
            confusion[other][label] for other in labels if other != label
        )
        false_negative = sum(
            confusion[label][other] for other in labels if other != label
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0.0
        )
        per_class[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": sum(confusion[label].values()),
        }

    return {
        "sample_count": len(expected),
        "accuracy": round(
            sum(actual == predicted_label for actual, predicted_label in zip(expected, predicted))
            / len(expected), 3
        ) if expected else None,
        "macro_f1": round(
            statistics.mean(item["f1"] for item in per_class.values()), 3
        ) if per_class else None,
        "labels": labels,
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def ordinal_severity_metrics(expected: list[str], predicted: list[str]) -> dict:
    paired = [
        (actual, prediction)
        for actual, prediction in zip(expected, predicted)
        if actual in ORDINAL_SEVERITIES and prediction in ORDINAL_SEVERITIES
    ]
    if not paired:
        return {"sample_count": 0, "mae": None, "weighted_kappa": None}

    indices = {label: index for index, label in enumerate(ORDINAL_SEVERITIES)}
    absolute_errors = [
        abs(indices[actual] - indices[prediction])
        for actual, prediction in paired
    ]
    labels = ORDINAL_SEVERITIES
    n = len(paired)
    observed_disagreement = sum(
        abs(indices[actual] - indices[prediction]) / (len(labels) - 1)
        for actual, prediction in paired
    ) / n
    expected_counts = {label: 0 for label in labels}
    predicted_counts = {label: 0 for label in labels}
    for actual, prediction in paired:
        expected_counts[actual] += 1
        predicted_counts[prediction] += 1
    expected_disagreement = sum(
        abs(indices[actual] - indices[prediction]) / (len(labels) - 1)
        * expected_counts[actual] * predicted_counts[prediction]
        for actual in labels
        for prediction in labels
    ) / (n * n)
    kappa = (
        1 - observed_disagreement / expected_disagreement
        if expected_disagreement else (1.0 if observed_disagreement == 0 else None)
    )
    return {
        "sample_count": n,
        "mae": round(statistics.mean(absolute_errors), 3),
        "weighted_kappa": round(kappa, 3) if kappa is not None else None,
        "excluded_unknown_count": len(expected) - n,
    }


def validate_reference(row: dict, row_number: int) -> dict:
    reference = {field: (row.get(field) or "").strip() for field in REFERENCE_FIELDS}
    if not all(reference.values()):
        return reference

    reference["expected_damage_class"] = reference["expected_damage_class"].casefold()
    reference["expected_severity"] = reference["expected_severity"].capitalize()
    reference["expected_description_consistency"] = (
        reference["expected_description_consistency"].casefold()
    )
    allowed = {
        "expected_damage_class": DAMAGE_CLASSES,
        "expected_severity": SEVERITIES,
        "expected_description_consistency": CONSISTENCY_LABELS,
    }
    for field, values in allowed.items():
        if reference[field] not in values:
            raise ValueError(
                f"CSV row {row_number}: {field} must be one of "
                f"{', '.join(values)}; received {reference[field]!r}."
            )
    return reference


def reference_metrics(results: list[dict]) -> dict:
    labeled_result_count = sum(
        all(result["reference"].get(field) for field in REFERENCE_FIELDS)
        for result in results
    )
    labeled_pairs = []
    for result in results:
        reference = result["reference"]
        if not all(reference.get(field) for field in REFERENCE_FIELDS):
            continue
        prediction = result.get("reference_comparison")
        if prediction is not None:
            labeled_pairs.append((reference, prediction))

    if not labeled_pairs:
        return {
            "dataset_case_count": len(results),
            "human_labeled_case_count": labeled_result_count,
            "unlabeled_case_count": len(results) - labeled_result_count,
            "annotated_case_count": 0,
            "metrics": None,
            "note": "Fill the expected_* CSV columns with human-verified labels to calculate accuracy metrics.",
        }

    return {
        "dataset_case_count": len(results),
        "human_labeled_case_count": labeled_result_count,
        "unlabeled_case_count": len(results) - labeled_result_count,
        "annotated_case_count": len(labeled_pairs),
        "metrics": {
            "damage_class": classification_metrics(
                [ref["expected_damage_class"] for ref, _ in labeled_pairs],
                [pred["damage_class"] for _, pred in labeled_pairs],
            ),
            "severity": {
                "classification": classification_metrics(
                    [ref["expected_severity"] for ref, _ in labeled_pairs],
                    [pred["severity"] for _, pred in labeled_pairs],
                ),
                "ordinal": ordinal_severity_metrics(
                    [ref["expected_severity"] for ref, _ in labeled_pairs],
                    [pred["severity"] for _, pred in labeled_pairs],
                ),
            },
            "description_consistency": classification_metrics(
                [ref["expected_description_consistency"] for ref, _ in labeled_pairs],
                [pred["description_consistency"] for _, pred in labeled_pairs],
            ),
        },
        "note": (
            "Metrics compare the first successful vision run per image to "
            "the human-provided reference labels. Damage classes are mapped "
            "from the agent's free-text damage_type using keyword rules."
        ),
    }


def evaluate_case(
    client: genai.Client,
    vision_agent: VisionAgent,
    judge_model: str,
    image_path: Path,
    customer_description: str,
    repeats: int,
    reference: dict,
) -> dict:
    case_result = {
        "image_path": str(image_path),
        "customer_description": customer_description,
        "reference": reference,
        "runs": [],
        "judge_score": None,
        "errors": [],
    }
    successful_outputs = []
    vision_latencies = []

    try:
        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB")
            image.load()
    except Exception as exc:
        case_result["errors"].append(
            {"stage": "image", "error": f"{type(exc).__name__}: {exc}"}
        )
        case_result["stability"] = stability_metrics(successful_outputs)
        case_result["reference_comparison"] = None
        return case_result

    for run_number in range(1, repeats + 1):
        started = time.perf_counter()
        try:
            analysis: VisionAnalysis = vision_agent.analyze(
                image=image,
                customer_description=customer_description,
            )
            output = analysis.model_dump(mode="json")
            elapsed = time.perf_counter() - started
            vision_latencies.append(elapsed)
            successful_outputs.append(output)
            case_result["runs"].append(
                {
                    "run": run_number,
                    "status": "success",
                    "latency_seconds": round(elapsed, 3),
                    "complete": is_complete(output),
                    "agent_output": output,
                }
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            vision_latencies.append(elapsed)
            error = f"{type(exc).__name__}: {exc}"
            case_result["runs"].append(
                {
                    "run": run_number,
                    "status": "error",
                    "latency_seconds": round(elapsed, 3),
                    "error": error,
                }
            )
            case_result["errors"].append(
                {"stage": "vision", "run": run_number, "error": error}
            )

    case_result["vision_latency_seconds"] = {
        "mean": round(statistics.mean(vision_latencies), 3)
        if vision_latencies else None,
        "median": round(statistics.median(vision_latencies), 3)
        if vision_latencies else None,
    }
    case_result["stability"] = stability_metrics(successful_outputs)
    if successful_outputs and all(reference.get(field) for field in REFERENCE_FIELDS):
        first_output = successful_outputs[0]
        case_result["reference_comparison"] = {
            "damage_class": predict_damage_class(first_output["damage_type"]),
            "severity": first_output["severity"].capitalize(),
            "description_consistency": predict_consistency_label(
                first_output["description_consistency"]
            ),
        }
    else:
        case_result["reference_comparison"] = None

    if successful_outputs:
        analysis = VisionAnalysis.model_validate(successful_outputs[0])
        judge_started = time.perf_counter()
        judge_prompt = (
            f"{JUDGE_INSTRUCTIONS}\n\n"
            f"Customer description:\n{customer_description}\n\n"
            "Vision Agent output (JSON):\n"
            f"{analysis.model_dump_json(indent=2)}"
        )
        for attempt in range(JUDGE_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=judge_model,
                    contents=[judge_prompt, image],
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": VisionJudgeScore,
                    },
                )
                if not response.text:
                    raise RuntimeError("LLM judge returned an empty response.")
                score = VisionJudgeScore.model_validate_json(response.text)
                case_result["judge_score"] = score.model_dump(mode="json")
                break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                is_temporary = any(
                    indicator in error.lower()
                    for indicator in ("503", "429", "unavailable", "high demand", "rate limit")
                )
                if is_temporary and attempt < JUDGE_RETRIES:
                    wait_seconds = JUDGE_RETRY_DELAY_SECONDS * (attempt + 1)
                    print(
                        f"[LLM Judge] Temporary error; retry "
                        f"{attempt + 1}/{JUDGE_RETRIES} in {wait_seconds}s..."
                    )
                    time.sleep(wait_seconds)
                    continue

                case_result["errors"].append(
                    {"stage": "judge", "error": error}
                )
                break
        case_result["judge_latency_seconds"] = round(
            time.perf_counter() - judge_started, 3
        )

    return case_result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the Vision Agent with a Gemini LLM judge."
    )
    parser.add_argument("dataset", type=Path, help="CSV with image_path and customer_description columns")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("vision_evaluation_results.json"),
        help="Output JSON file (default: vision_evaluation_results.json)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Vision analyses per case for stability measurement (default: 3; minimum: 2)",
    )
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("--repeats must be at least 2 to measure stability.")

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in the environment or .env file.")

    judge_model = os.getenv("GEMINI_JUDGE_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)
    vision_agent = VisionAgent()

    dataset_path = args.dataset.resolve()
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as dataset_file:
        reader = csv.DictReader(dataset_file)
        required_columns = {"image_path", "customer_description", *REFERENCE_FIELDS}
        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "Dataset CSV must have these columns: image_path, customer_description."
            )

        results = []
        for row_number, row in enumerate(reader, start=2):
            image_value = (row.get("image_path") or "").strip()
            description = (row.get("customer_description") or "").strip()
            if not image_value or not description:
                raise ValueError(
                    f"Dataset row {row_number} has an empty image_path or customer_description."
                )

            image_path = Path(image_value)
            if not image_path.is_absolute():
                image_path = dataset_path.parent / image_path
            reference = validate_reference(row, row_number)

            print(f"Evaluating row {row_number}: {image_path}")
            results.append(
                evaluate_case(
                    client=client,
                    vision_agent=vision_agent,
                    judge_model=judge_model,
                    image_path=image_path,
                    customer_description=description,
                    repeats=args.repeats,
                    reference=reference,
                )
            )

    if not results:
        raise ValueError("The dataset contains no evaluation cases.")

    vision_runs = [
        run
        for result in results
        for run in result["runs"]
    ]
    successful_runs = [
        run for run in vision_runs if run["status"] == "success"
    ]
    successful_judges = [
        result["judge_score"]
        for result in results
        if result["judge_score"] is not None
    ]
    judge_averages = {
        field: round(
            sum(score[field] for score in successful_judges)
            / len(successful_judges),
            2,
        )
        for field in VisionJudgeScore.model_fields
        if field != "rationale"
    } if successful_judges else {}
    vision_latencies = [
        run["latency_seconds"] for run in vision_runs
    ]
    complete_runs = sum(run["complete"] for run in successful_runs)
    judge_latencies = [
        result["judge_latency_seconds"]
        for result in results
        if "judge_latency_seconds" in result
    ]
    all_errors = [
        {"image_path": result["image_path"], **error}
        for result in results
        for error in result["errors"]
    ]
    stability_values = [
        result["stability"]["pairwise_agreement"]
        for result in results
        if result["stability"]["pairwise_agreement"] is not None
    ]
    exact_stability_values = [
        result["stability"]["exact_output_pairwise_agreement"]
        for result in results
        if result["stability"]["exact_output_pairwise_agreement"] is not None
    ]

    report = {
        "cases_evaluated": len(results),
        "repeats_per_case": args.repeats,
        "judge_model": judge_model,
        "score_scale": "1 (very poor) to 5 (excellent)",
        "reference_evaluation": reference_metrics(results),
        "metrics": {
            "vision_run_success_rate": round(
                len(successful_runs) / len(vision_runs), 3
            ) if vision_runs else 0,
            "complete_output_rate": round(
                complete_runs / len(successful_runs), 3
            ) if successful_runs else None,
            "stability_pairwise_agreement_mean": round(
                statistics.mean(stability_values), 3
            ) if stability_values else None,
            "stability_exact_output_agreement_mean": round(
                statistics.mean(exact_stability_values), 3
            ) if exact_stability_values else None,
            "vision_latency_seconds": {
                "mean": round(statistics.mean(vision_latencies), 3)
                if vision_latencies else None,
                "median": percentile(vision_latencies, 50),
                "p95": percentile(vision_latencies, 95),
            },
            "judge_latency_seconds": {
                "mean": round(statistics.mean(judge_latencies), 3)
                if judge_latencies else None,
                "median": percentile(judge_latencies, 50),
                "p95": percentile(judge_latencies, 95),
            },
            "judge_average_scores_1_to_5": judge_averages,
            "error_count": len(all_errors),
            "errors": all_errors,
            "note": (
                "LLM-judge scores and repeatability are indicators, not "
                "ground-truth accuracy measurements. Reference metrics "
                "are reported separately when human labels are provided."
            ),
        },
        "results": results,
    }

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nEvaluated {len(results)} cases.")
    print(json.dumps(report["reference_evaluation"], ensure_ascii=False, indent=2))
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
