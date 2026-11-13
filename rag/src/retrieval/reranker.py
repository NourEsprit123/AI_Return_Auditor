from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from FlagEmbedding import FlagReranker


class Candidate(TypedDict):
    chunk_id: str
    title: str
    score: float
    text: str


class RankedCandidate(Candidate):
    rerank_score: float


@lru_cache(maxsize=1)
def _get_reranker() -> FlagReranker:
    from FlagEmbedding import FlagReranker

    return FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)

def rerank(
    query: str,
    candidates: list[Candidate],
    top_k: int = 5,
) -> list[RankedCandidate]:
    """
    candidates = list of dicts coming from hybrid_search (or dense_search)
    Returns the re-ordered top_k results with new scores.
    """
    if not candidates:
        return []

    # Prepare pairs (query, text)
    pairs = [(query, candidate["text"]) for candidate in candidates]

    # Get scores from the cross-encoder
    scores = _get_reranker().compute_score(pairs, normalize=True)
    if scores is None:
        raise RuntimeError("The reranker did not return scores.")

    ranked_candidates: list[RankedCandidate] = [
        {**candidate, "rerank_score": float(scores[index])}
        for index, candidate in enumerate(candidates)
    ]

    reranked = sorted(
        ranked_candidates,
        key=lambda candidate: candidate["rerank_score"],
        reverse=True,
    )[:top_k]
    return reranked