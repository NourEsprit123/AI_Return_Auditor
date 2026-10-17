import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def expand_query(query: str, num_variants: int = 2) -> list[str]:
    """
    Returns the original query + a few rewritten versions
    that are better for retrieval.
    """
    if not query.strip():
        return []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured for RAG query expansion.")

    prompt = f"""You are a query rewriter for a precise Return & Refund policy retrieval system.

            Your job is to rewrite the user's question into {num_variants} high-quality search queries that will help a hybrid retriever (dense + BM25) find the correct policy sections.

            ### Rules
            1. Preserve the original intent exactly.
            2. Use precise policy terminology whenever possible:
            - VIS / Visual Inspection Score
            - RMA
            - restocking fee
            - Final Sale
            - Original Condition
            - return window
            - non-returnable
            - defective / damaged in transit
            3. Explicitly include (when present in the original):
            - the product or item type
            - the requested action (return, refund, exchange, etc.)
            - the reason (defective, damaged, opened, missing parts, wrong item, change of mind, etc.)
            - any time information (e.g. 3 days ago, after 35 days, within 14 days)
            4. Prefer short, keyword-rich queries over full sentences.
            5. Do not add information that is not present in the original question.
            6. Avoid filler words.

            ### Output format
            Return only the rewritten queries, one per line. Do not number them or add any extra text.

            User question: {query}"""

    response = Groq(api_key=api_key).chat.completions.create(
        model="qwen/qwen3.8-27b",   # Active, highly compatible model on Groq
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=150
    )

    content = response.choices[0].message.content or ""
    variants = [
        line.strip()
        for line in content.split("\n")
        if line.strip()
    ]

    # Always keep the original query first
    return [query] + variants[:num_variants]