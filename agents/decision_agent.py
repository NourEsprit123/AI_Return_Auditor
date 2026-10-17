import asyncio
import json
import os
from dotenv import load_dotenv
from groq import AsyncGroq
from SCprompting.config import HIGH_VALUE_THRESHOLD_USD
from SCprompting.model_runner import generate_reasoning_paths
from SCprompting.consensus_engine import evaluate_consensus
from agents.llm_judge import judge_consensus

load_dotenv()

def decision_input_formatting(prompt: str, context: str) -> str:
    """Combine claim data and retrieved policies without an extra model call."""
    try:
        claim = json.loads(prompt)
    except json.JSONDecodeError:
        claim = prompt

    try:
        policies = json.loads(context)
    except json.JSONDecodeError:
        policies = context

    return json.dumps(
        {"user_claim": claim, "retrieved_policies": policies},
        ensure_ascii=False,
    )

async def audit_return_request(groq_api_key: str, raw_prompt: str, rag_context: str, item_value: float = 0.0) -> dict:
    """
    Main entry point orchestrating the entire decision audit workflow.
    """
    if not groq_api_key:
        raise ValueError("A Groq API key is required to audit a return request.")

    # Keep the pipeline inputs intact; no formatter model call is needed.
    formatted_json_input = decision_input_formatting(raw_prompt, rag_context)

    # Step 2: Run parallel Self-Consistency samples using async client
    client_async = AsyncGroq(api_key=groq_api_key)
    samples = await generate_reasoning_paths(client_async, formatted_json_input)

    # Step 3: Evaluate consensus and business guardrails.
    final_output = evaluate_consensus(samples, item_value=item_value, high_value_limit=HIGH_VALUE_THRESHOLD_USD)

    # Step 4: Require the local compliance audit before exposing a decision.
    formatted_inputs = json.loads(formatted_json_input)
    claim = formatted_inputs.get("user_claim")
    policies = formatted_inputs.get("retrieved_policies")
    vision = claim.get("vision_agent_json") if isinstance(claim, dict) else None
    return await judge_consensus(final_output, claim, vision, policies)

# Local Test Execution
if __name__ == "__main__":
    api_key = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")

    test_prompt = "Order #98231, Leather Biker Jacket. The zipper is completely broken and torn on arrival."
    test_rag = "POL-DAMAGED-01: Items damaged on arrival are eligible for full refund or free replacement within 30 days. Photo evidence required."

    if api_key != "your_groq_api_key_here":
        result = asyncio.run(audit_return_request(api_key, test_prompt, test_rag, item_value=180.0))
        print("Audit Result:", result)
    else:
        print("Please set your GROQ_API_KEY environment variable to test locally.")