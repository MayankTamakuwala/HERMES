"""Retrieval and ranking evaluation metrics."""

from __future__ import annotations

import numpy as np


def recall_at_k(relevant_id: int, retrieved_ids: list[int], k: int) -> float:
    """1.0 if the relevant id appears in the top-k retrieved, else 0.0."""
    return 1.0 if relevant_id in retrieved_ids[:k] else 0.0


def mrr_at_k(relevant_id: int, retrieved_ids: list[int], k: int) -> float:
    """Reciprocal rank of the relevant id within the top-k, or 0 if absent."""
    for rank, rid in enumerate(retrieved_ids[:k], 1):
        if rid == relevant_id:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(relevant_id: int, retrieved_ids: list[int], k: int) -> float:
    """Binary-relevance nDCG@k: 1 if relevant_id is present, scored by position."""
    dcg = 0.0
    for rank, rid in enumerate(retrieved_ids[:k], 1):
        if rid == relevant_id:
            dcg = 1.0 / np.log2(rank + 1)
            break
    # Ideal DCG is 1/log2(2) = 1.0 (relevant doc at position 1)
    idcg = 1.0 / np.log2(2)
    return dcg / idcg if idcg > 0 else 0.0


def compute_metrics(
    queries: list[dict],
    ks: list[int] = (5, 10, 50),
) -> dict[str, float]:
    """Compute aggregate metrics over a list of query results.

    Each query dict must have:
        - relevant_chunk_id: int
        - retrieval_ids: list[int]  (ordered by retrieval rank)
        - rerank_ids: list[int] | None  (ordered by rerank rank)
    """
    results: dict[str, list[float]] = {}

    for q in queries:
        rel_id = q["relevant_chunk_id"]
        ret_ids = q["retrieval_ids"]
        rerank_ids = q.get("rerank_ids") or ret_ids

        for k in ks:
            key = f"recall@{k}"
            results.setdefault(key, []).append(recall_at_k(rel_id, ret_ids, k))

        results.setdefault("mrr@10_retrieval", []).append(mrr_at_k(rel_id, ret_ids, 10))
        results.setdefault("mrr@10_rerank", []).append(mrr_at_k(rel_id, rerank_ids, 10))
        results.setdefault("ndcg@10_rerank", []).append(ndcg_at_k(rel_id, rerank_ids, 10))

    return {k: round(float(np.mean(v)), 4) for k, v in sorted(results.items())}
