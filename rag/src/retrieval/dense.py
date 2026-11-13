from rag.src.embeddings import (
    chunk_ids,
    chunkedJSON,
    get_embedding_model,
    get_vector_collection,
)


def dense_search(query: str, top_k: int = 10, min_score: float | None = None):
    if not query or top_k <= 0 or not chunk_ids:
        return []

    query_output = get_embedding_model().encode(
        [query],
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    query_vec = query_output["dense_vecs"][0].tolist()
    results = get_vector_collection().query(
        query_embeddings=[query_vec],
        n_results=min(top_k, len(chunk_ids)),
        include=["documents", "metadatas", "distances"],
    )

    chunk_index_by_id = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
    matches = []
    for chunk_id, text, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = 1.0 - distance
        if min_score is not None and score < min_score:
            continue
        matches.append({
            "chunk_id": chunk_id,
            "title": metadata.get("title", ""),
            "score": float(score),
            "text": text,
            "index": chunk_index_by_id[chunk_id],
        })
    return matches