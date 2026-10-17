import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from rag.src.embeddings import (
    chunk_ids,
    chunkedJSON,
    get_embedding_model,
    get_embeddings,
    texts,
)


def dense_search(query: str, top_k: int = 10, min_score: float | None = None):
    if not query:
        return []

    query_output = get_embedding_model().encode(
        [query],
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    query_vec = np.array(query_output["dense_vecs"][0], dtype=np.float32).reshape(1, -1)

    scores = cosine_similarity(query_vec, get_embeddings())[0]
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if min_score is not None and scores[idx] < min_score:
            break  # sorted descending, so everything after is lower
        results.append({
            "chunk_id": chunk_ids[idx],
            "title": chunkedJSON[idx].get("title", ""),
            "score": float(scores[idx]),
            "text": texts[idx],
            "index": int(idx),
        })
    return results