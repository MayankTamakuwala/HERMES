"""Result fusion strategies for hybrid retrieval."""

from __future__ import annotations

def reciprocal_rank_fusion(
    results_lists: list[list[tuple[int, float]]],
    k: int = 60,
    top_n: int = 100,
) -> list[tuple[int, float]]:
    """Fuse multiple ranked lists using Reciprocal Rank Fusion.

    Each input list contains (doc_id, score) tuples sorted by score descending.
    Returns fused (doc_id, rrf_score) tuples sorted by RRF score descending.

    Parameters
    ----------
    results_lists:
        List of ranked result lists, each containing (id, score) pairs.
    k:
        RRF constant (higher = more uniform weighting across ranks).
    top_n:
        Maximum number of results to return.
    """
    rrf_scores: dict[int, float] = {}
    for ranked_list in results_lists:
        for rank, (doc_id, _score) in enumerate(ranked_list):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results[:top_n]
