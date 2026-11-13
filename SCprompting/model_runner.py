import json
import asyncio
from groq import AsyncGroq
from .config import GROQ_MODEL, NUM_SAMPLES, TEMPERATURE
from .prompt_templates import AUDITOR_SYSTEM_PROMPT, get_auditor_prompt

async def run_single_sample(client: AsyncGroq, formatted_input: str) -> dict:
    """Runs a single inference pass to generate one reasoning trajectory."""
    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                {"role": "user", "content": get_auditor_prompt(formatted_input)}
            ],
            response_format={"type": "json_object"},
            temperature=TEMPERATURE
        )
        content = response.choices[0].message.content or ""
        return json.loads(content)
    except Exception as e:
        return {"error": str(e), "decision": "ESCALATE_HUMAN"}

async def generate_reasoning_paths(client: AsyncGroq, formatted_input: str) -> list:
    """Spawns N concurrent sampling tasks to collect distinct Chain-of-Thought outputs."""
    tasks = [run_single_sample(client, formatted_input) for _ in range(NUM_SAMPLES)]
    results = await asyncio.gather(*tasks)
    if not any("decision" in result and "error" not in result for result in results):
        errors = "; ".join(result.get("error", "Invalid model response") for result in results)
        raise RuntimeError(f"All decision samples failed: {errors}")
    return results