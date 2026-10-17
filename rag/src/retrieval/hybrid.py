

from rag.src.embeddings import chunkedJSON
from rag.src.retrieval.dense import dense_search
from rag.src.retrieval.sparse import sparse_search


ID_TO_CHUNK = {c["chunk_id"]: c for c in chunkedJSON}

def hybrid_search(query: str, top_k: int = 15, dense_weight: float = 0.4, rrf_k: int = 20):
    if not query:
        return []

    dense_results = dense_search(query, top_k=top_k)
    bm25_results = sparse_search(query, top_k=top_k)

    fused = {}
    for rank, r in enumerate(dense_results, start=1):
        fused[r["chunk_id"]] = fused.get(r["chunk_id"], 0) + dense_weight / (rrf_k + rank)
    for rank, r in enumerate(bm25_results, start=1):
        fused[r["chunk_id"]] = fused.get(r["chunk_id"], 0) + (1 - dense_weight) / (rrf_k + rank)

    sorted_cids = sorted(fused, key=lambda cid: fused[cid], reverse=True)[:int(top_k)]
    return [
        {
            "chunk_id": cid,
            "title": ID_TO_CHUNK[cid].get("title", ""),
            "score": fused[cid],
            "text": ID_TO_CHUNK[cid]["text"],
        }
        for cid in sorted_cids
    ]