import json
from groq import Groq

from AI_Return_Auditor.SCprompting.config import GROQ_MODEL

client = Groq(api_key="GROQ_API_KEY")

def decision_input_formatting(prompt: str, context: str) -> str:
    """
    Transforms raw user input and RAG context into a standardized 
    JSON payload suitable for the Self-Consistency Decision Agent.

    Args:
        prompt (str): The user's original query, statement, and order details.
        context (str): The raw text chunks retrieved by the RAG agent.

    Returns:
        str: A JSON-formatted string matching the decision agent's schema.
    """
    system_prompt = """
    You are a data structuring assistant for an e-commerce return audit system.
    Your task is to parse the raw user query and retrieved RAG policies into a strict JSON object.

    The output JSON must strictly follow this schema:
    {
      "user_claim": {
        "order_id": "Extract order ID if present, otherwise null",
        "item_name": "Extract item name if present, otherwise null",
        "user_statement": "The core user statement or complaint",
        "state_declared_by_user": "Declared state (e.g., Damaged, Defective, Wrong Size, Changed Mind)",
        "visual_inspection_summary": "Summary of visual details or image findings mentioned in the prompt"
      },
      "retrieved_policies": [
        {
          "policy_id": "Extract policy ID or identifier if present, otherwise 'POL-GENERAL'",
          "rule": "The text of the policy rule"
        }
      ]
    }

    Return ONLY valid JSON. Do not include markdown code block syntax (like ```json) or conversational text.
    """

    user_message = f"--- USER QUERY & DETAILS ---\n{prompt}\n\n--- RETRIEVED RAG CONTEXT ---\n{context}"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL, # Fast and highly accurate for structural parsing
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.09, # Low temperature for deterministic, structured formatting
            top_p=0.9  
        )

        content = response.choices[0].message.content or ""
        # Return the clean JSON string
        return content

    except Exception as e:
        # Fallback error structure if parsing fails
        fallback_payload = {
            "error": f"Failed to format input: {str(e)}",
            "raw_prompt": prompt,
            "raw_context": context
        }
        return json.dumps(fallback_payload)