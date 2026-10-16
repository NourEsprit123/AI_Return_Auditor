"""
evaluate_retrieval.py
---------------------
RAG Retrieval Evaluation

Evaluates the retrieval quality of Agent 2 (Policy RAG Agent) using
standard Information Retrieval metrics:

  - Hit@1  : Is the most relevant chunk ranked #1?
  - Hit@3  : Is the most relevant chunk in the top 3?
  - MRR    : Mean Reciprocal Rank (average of 1/rank of first hit)

Two chunking strategies are compared:
  - Strategy A: 500 chars / 100 overlap  (default)
  - Strategy B: 1000 chars / 200 overlap (larger chunks)

Results are printed as a table suitable for the technical report annex.

Run with:
  python evaluate_retrieval.py
"""

import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from rag.retriever import PolicyVectorStore, Reranker, ModularRAGRetriever
from rag.documents import load_documents, load_documents_large_chunks
from rag.embeddings import get_embedding_model


# ============================================================
# TEST QUERIES
# Each query has:
#   - query         : the search string
#   - expected_doc  : which policy file should be the top result
#   - expected_kw   : a keyword that should appear in the top chunk
# ============================================================

TEST_QUERIES = [
    {
        "id": "Q1",
        "query": "Return policy for eyeglasses with broken or detached temple arm",
        "expected_doc": "return_policy.txt",
        "expected_kw": "eyeglasses",
        "description": "Broken accessory — specific product mention",
    },
    {
        "id": "Q2",
        "query": "Refund conditions for shoes received with visible stain cosmetic damage",
        "expected_doc": "refund_policy.txt",
        "expected_kw": "stain",
        "description": "Cosmetic damage refund — stain on footwear",
    },
    {
        "id": "Q3",
        "query": "Warranty coverage for manufacturing defect smartphone cracked screen",
        "expected_doc": "warranty_policy.txt",
        "expected_kw": "manufacturing defect",
        "description": "Warranty claim — electronics defect",
    },
    {
        "id": "Q4",
        "query": "Return window expired 30 days delivery date exception",
        "expected_doc": "return_policy.txt",
        "expected_kw": "30",
        "description": "Return window — deadline and exceptions",
    },
    {
        "id": "Q5",
        "query": "Full refund non-functional product complete damage safety risk",
        "expected_doc": "refund_policy.txt",
        "expected_kw": "full refund",
        "description": "Full refund — non-functional product",
    },
    {
        "id": "Q6",
        "query": "Latent defect warranty claim appears after normal use hinge failure",
        "expected_doc": "warranty_policy.txt",
        "expected_kw": "latent",
        "description": "Latent defect — appears during normal use",
    },
]


# ============================================================
# EVALUATION HELPERS
# ============================================================

def find_hit_rank(chunks, expected_doc: str, expected_kw: str) -> int:
    """
    Find the rank (1-indexed) of the first chunk that matches the
    expected document AND contains the expected keyword.
    Returns 0 if not found in top K.
    """
    for rank, chunk in enumerate(chunks, start=1):
        doc_match = expected_doc in chunk.source
        kw_match  = expected_kw.lower() in chunk.text.lower()
        if doc_match and kw_match:
            return rank
    return 0


def compute_metrics(results: list[dict]) -> dict:
    """Compute Hit@1, Hit@3, MRR from a list of result dicts."""
    hit1 = sum(1 for r in results if r["rank"] == 1) / len(results)
    hit3 = sum(1 for r in results if 1 <= r["rank"] <= 3) / len(results)
    mrr  = sum(1 / r["rank"] for r in results if r["rank"] > 0) / len(results)
    return {"Hit@1": hit1, "Hit@3": hit3, "MRR": mrr}


# ============================================================
# RUN EVALUATION FOR ONE STRATEGY
# ============================================================

def evaluate_strategy(strategy_name: str, chunks_loader, top_k: int = 5) -> list[dict]:
    """Run all test queries against a given chunking strategy."""

    print(f"\n{'='*60}")
    print(f"Strategy: {strategy_name}")
    print(f"{'='*60}")

    # Build vector store with this strategy's chunks
    embedding_model = get_embedding_model()
    # Clean collection name — ChromaDB only allows [a-zA-Z0-9._-]
    safe_name = "".join(c if c.isalnum() else "" for c in strategy_name)[:40]
    store = PolicyVectorStore(embedding_model=embedding_model,
                              collection_name=f"eval{safe_name}")
    store.reset()

    chunks = chunks_loader()
    store.build(chunks)
    print(f"Indexed {store.collection.count()} chunks.")

    reranker  = Reranker()
    retriever = ModularRAGRetriever(vector_store=store, reranker=reranker)

    results = []

    for tq in TEST_QUERIES:
        retrieved = retriever.retrieve(tq["query"], top_k_retrieval=top_k, compress=False)
        rank = find_hit_rank(retrieved, tq["expected_doc"], tq["expected_kw"])

        result = {
            "id":          tq["id"],
            "description": tq["description"],
            "query":       tq["query"][:60] + "...",
            "expected":    tq["expected_doc"],
            "rank":        rank,
            "hit1":        rank == 1,
            "hit3":        1 <= rank <= 3,
            "top_chunk":   retrieved[0].source if retrieved else "—",
        }

        results.append(result)

        status = f"rank={rank}" if rank > 0 else "MISS"
        print(f"  [{tq['id']}] {status:8} | {tq['description']}")

    return results


# ============================================================
# PRINT TABLE
# ============================================================

def print_table(strategy_name: str, results: list[dict], metrics: dict):
    print(f"\n--- {strategy_name} ---")
    print(f"{'ID':<4} {'Hit@1':<6} {'Hit@3':<6} {'Rank':<6} {'Description'}")
    print("-" * 65)
    for r in results:
        h1 = "✓" if r["hit1"] else "✗"
        h3 = "✓" if r["hit3"] else "✗"
        rk = str(r["rank"]) if r["rank"] > 0 else "MISS"
        print(f"{r['id']:<4} {h1:<6} {h3:<6} {rk:<6} {r['description']}")
    print("-" * 65)
    print(f"     Hit@1={metrics['Hit@1']:.0%}  Hit@3={metrics['Hit@3']:.0%}  MRR={metrics['MRR']:.3f}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("AI Return Auditor — RAG Retrieval Evaluation")
    print("=" * 60)
    print(f"Test queries : {len(TEST_QUERIES)}")
    print(f"Metrics      : Hit@1, Hit@3, MRR")
    print(f"Strategies   : Fixed-size 500/100  vs  Fixed-size 1000/200")

    # Strategy A — 500/100 (default)
    results_a = evaluate_strategy("Strategy A: 500/100", load_documents)
    metrics_a = compute_metrics(results_a)

    # Strategy B — 1000/200 (larger chunks)
    results_b = evaluate_strategy("Strategy B: 1000/200", load_documents_large_chunks)
    metrics_b = compute_metrics(results_b)

    # Print comparison tables
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print_table("Strategy A — Fixed-size 500 chars / 100 overlap", results_a, metrics_a)
    print_table("Strategy B — Fixed-size 1000 chars / 200 overlap", results_b, metrics_b)

    # Summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Metric':<10} {'Strategy A (500/100)':<22} {'Strategy B (1000/200)'}")
    print("-" * 55)
    for metric in ["Hit@1", "Hit@3", "MRR"]:
        a = metrics_a[metric]
        b = metrics_b[metric]
        winner = "← A wins" if a > b else ("← B wins" if b > a else "tie")
        print(f"{metric:<10} {a:<22.3f} {b:<10.3f} {winner}")

    print("\nConclusion:")
    if metrics_a["MRR"] >= metrics_b["MRR"]:
        print("  Strategy A (500/100) produces better retrieval quality.")
        print("  Smaller chunks keep each policy rule focused and reduce noise.")
    else:
        print("  Strategy B (1000/200) produces better retrieval quality.")
        print("  Larger chunks preserve more context per retrieved segment.")

    print("\nEvaluation complete. Use these results in the technical report.")
