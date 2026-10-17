from rag.src.retrieval.query_expansion import expand_query
from rag.src.retrieval.hybrid import hybrid_search
from rag.src.retrieval.reranker import rerank


def advanced_retrieve(query: str, final_top_k: int = 4):
    """
    Complete pipeline:
    1. Query expansion
    2. Hybrid search on each expanded query
    3. Merge & deduplicate candidates
    4. Rerank
    5. Return final top_k
    """
    if not query.strip() or final_top_k <= 0:
        return []

    # 1. Expand
    expanded_queries = expand_query(query)

    # 2. Collect candidates from all expanded queries
    all_candidates = {}
    for q in expanded_queries:
        hybrid_results = hybrid_search(q, top_k=15)
        for r in hybrid_results:
            cid = r["chunk_id"]
            # keep the highest hybrid score if the same chunk appears multiple times
            if cid not in all_candidates or r["score"] > all_candidates[cid]["score"]:
                all_candidates[cid] = r

    candidates = list(all_candidates.values())

    # 3. Rerank
    final_results = rerank(query, candidates, top_k=final_top_k)

    return final_results