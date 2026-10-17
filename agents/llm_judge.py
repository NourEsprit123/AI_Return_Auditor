import asyncio
import ipaddress
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent.parent
VERDICT_PATH = BASE_DIR / "llm_judge_verdict.json"
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "compliant": {"type": "boolean"},
        "hallucination_detected": {"type": "boolean"},
        "policy_violation": {"type": "boolean"},
        "dangerous_contradiction": {"type": "boolean"},
        "findings": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": [
        "compliant",
        "hallucination_detected",
        "policy_violation",
        "dangerous_contradiction",
        "findings",
        "rationale",
    ],
}
JUDGE_SYSTEM_PROMPT = """
You are an independent, strict compliance auditor reviewing a return or refund decision.
Check the panel's final decision against the original customer claim, the original
vision findings, and only the supplied retrieved policy passages.

CRITICAL CONTEXT ON OUTCOMES:
- A decision of "REJECT" or "APPROVE_RETURN" or "APPROVE_REFUND" are ALL equally valid. 
- A decision to "REJECT" a claim is 100% compliant and safe if the policy and evidence dictate that the return is ineligible (e.g., normal wear and tear, out-of-window requests, customer-induced damage, or missing required conditions). 
- Do NOT flag a decision as non-compliant simply because it denies the customer's request or results in a rejection.

Answer the binary compliance question: is the panel's decision safe, well-reasoned, and supported by the evidence and policies?
Set compliant=false only if the decision relies on invented evidence, flatly violates a provided policy, or has a dangerous contradiction with the claim or vision findings.
Do not treat missing information as proof; flag it only when it makes the decision unsafe.
Do not invent policies. A disagreement without a concrete evidence-based safety or
policy issue is not by itself non-compliance.

Return only the required JSON object. Keep findings and rationale concise and factual.
"""


class LLMJudgeError(RuntimeError):
    """Raised when the local compliance judge cannot produce a valid verdict."""


def _write_verdict(report: dict[str, Any]) -> None:
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=VERDICT_PATH.parent,
            prefix=f".{VERDICT_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(report, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, VERDICT_PATH)
    except OSError as exc:
        raise LLMJudgeError(f"Could not write the LLM judge report: {exc}") from exc
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _local_ollama_url() -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LLMJudgeError("OLLAMA_BASE_URL must be a valid local HTTP(S) URL.")
    hostname = parsed.hostname.lower()
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname == "localhost"
    if not is_loopback:
        raise LLMJudgeError("The compliance judge must use a local Ollama URL.")
    return f"{base_url}/api/chat"


def _parse_judge_response(content: str) -> dict[str, Any]:
    try:
        verdict = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMJudgeError("Ollama returned invalid JSON for the compliance verdict.") from exc
    if not isinstance(verdict, dict):
        raise LLMJudgeError("Ollama's compliance verdict must be a JSON object.")

    boolean_fields = (
        "compliant",
        "hallucination_detected",
        "policy_violation",
        "dangerous_contradiction",
    )
    if any(type(verdict.get(field)) is not bool for field in boolean_fields):
        raise LLMJudgeError("Ollama's verdict is missing a required boolean compliance finding.")
    if not isinstance(verdict.get("findings"), list) or any(
        not isinstance(finding, str) for finding in verdict["findings"]
    ):
        raise LLMJudgeError("Ollama's verdict findings must be a list of strings.")
    if not isinstance(verdict.get("rationale"), str):
        raise LLMJudgeError("Ollama's verdict rationale must be a string.")
    return verdict


def _request_verdict(payload: dict[str, Any], model: str) -> dict[str, Any]:
    request_body = {
        "model": model,
        "stream": False,
        "format": VERDICT_SCHEMA,
        "options": {
            "temperature": 0.15,       # minimum tolerance for creativity; pure deterministic logic.
            "top_p": 0.9,              # Restricts vocabulary choice to the top 20 most likely tokens, eliminating random drift.
            "repeat_penalty": 1.1,    # Prevents the model from getting stuck repeating phrases in its rationale text.
            "num_predict": 300,       # Caps the maximum output tokens (the judge only needs a short JSON response, speeding it up).
            "seed": 42                # Forces a fixed seed so identical cases always yield identical judge logic.
        },
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    request = Request(
        _local_ollama_url(),
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise LLMJudgeError(f"Local Ollama compliance check failed: {exc}") from exc

    message = response_body.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise LLMJudgeError("Ollama returned an empty compliance verdict.")
    return _parse_judge_response(content)


def _run_judge(
    consensus: dict[str, Any],
    claim: Any,
    vision: Any,
    policies: Any,
) -> dict[str, Any]:
    model = os.getenv("OLLAMA_MODEL", "").strip()
    original_decision = str(consensus.get("decision", "UNKNOWN"))
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "model": model or None,
        "consensus_decision": original_decision,
        "final_decision": "ESCALATE_HUMAN",
        "override_applied": False,
    }
    _write_verdict(report)

    try:
        if not model:
            raise LLMJudgeError(
                "OLLAMA_MODEL is not configured. Set it to a model installed in local Ollama."
            )
        verdict = _request_verdict(
            {
                "consensus_decision": consensus,
                "original_customer_claim": claim,
                "vision_findings": vision,
                "retrieved_policy_passages": policies,
            },
            model,
        )
        override = (
            not verdict["compliant"]
            or verdict["hallucination_detected"]
            or verdict["policy_violation"]
            or verdict["dangerous_contradiction"]
        )
        final_decision = "ESCALATE_HUMAN" if override else original_decision
        report.update(
            {
                "status": "completed",
                **verdict,
                "verdict": "ESCALATE" if override else "PASS",
                "final_decision": final_decision,
                "override_applied": override,
            }
        )
        _write_verdict(report)
        if override:
            return {
                **consensus,
                "status": "ESCALATED",
                "decision": "ESCALATE_HUMAN",
                "customer_message": (
                    "Your request needs an additional specialist review. "
                    "We’ll share an update when it’s complete."
                ),
                "reasoning": "An additional specialist review is needed before a final outcome can be provided.",
                "reasoning_summary": "An additional specialist review is needed before a final outcome can be provided.",
            }
        return consensus
    except Exception as exc:
        report.update(
            {
                "status": "error",
                "verdict": "UNAVAILABLE",
                "final_decision": "ESCALATE_HUMAN",
                "override_applied": True,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        _write_verdict(report)
        raise


async def judge_consensus(
    consensus: dict[str, Any],
    claim: Any,
    vision: Any,
    policies: Any,
) -> dict[str, Any]:
    """Run the local compliance audit and escalate whenever it flags or fails."""
    return await asyncio.to_thread(_run_judge, consensus, claim, vision, policies)