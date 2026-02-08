"""Run the full evaluation pipeline and produce a markdown report."""

from __future__ import annotations

import json
import time
from pathlib import Path

from hermes.config import HermesConfig
from hermes.eval.dataset import EvalPair, generate_eval_dataset, load_eval_dataset, save_eval_dataset
from hermes.eval.metrics import compute_metrics
from hermes.index.metadata_store import MetadataStore
from hermes.logging import get_logger
from hermes.search.pipeline import SearchPipeline
from hermes.search.schemas import SearchRequest

log = get_logger(__name__)


def run_evaluation(
    config: HermesConfig,
    repo_path: Path | None = None,
    output_dir: Path = Path("reports"),
    eval_dataset_path: Path | None = None,
    max_queries: int = 200,
) -> Path:
    """Execute evaluation and write the markdown report.

    Returns the path to the generated report.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    store = MetadataStore(config.artifacts_dir / "metadata.db")

    # Load or generate eval dataset
    if eval_dataset_path and eval_dataset_path.exists():
        log.info("loading_eval_dataset", path=str(eval_dataset_path))
        pairs = load_eval_dataset(eval_dataset_path)
    else:
        log.info("generating_eval_dataset")
        pairs = generate_eval_dataset(store, max_queries=max_queries)
        ds_path = output_dir / "eval_dataset.json"
        save_eval_dataset(pairs, ds_path)

    if not pairs:
        raise ValueError("No evaluation pairs available")

    # Initialize pipeline
    pipeline = SearchPipeline(config)

    # Run queries and collect results
    query_results: list[dict] = []
    latencies: list[float] = []

    for pair in pairs:
        req = SearchRequest(
            query=pair.query,
            top_k_retrieve=config.search.top_k_retrieve,
            top_k_rerank=config.search.top_k_rerank,
        )

        t0 = time.perf_counter()
        resp = pipeline.search(req)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

        retrieval_ids = [r.chunk_id for r in sorted(resp.results, key=lambda x: x.retrieval_rank)]
        rerank_ids = [r.chunk_id for r in resp.results]  # already sorted by final_rank

        query_results.append({
            "relevant_chunk_id": pair.relevant_chunk_id,
            "retrieval_ids": retrieval_ids,
            "rerank_ids": rerank_ids,
        })

    # Compute metrics
    metrics = compute_metrics(query_results)

    # Latency stats
    latencies.sort()
    latency_stats = {
        "p50_ms": round(latencies[len(latencies) // 2], 1) if latencies else 0,
        "p95_ms": round(latencies[int(len(latencies) * 0.95)] , 1) if latencies else 0,
        "mean_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
    }

    # Generate report
    report_path = output_dir / "eval_report.md"
    _write_report(report_path, config, pairs, metrics, latency_stats)

    store.close()
    log.info("evaluation_complete", report=str(report_path))
    return report_path


def _write_report(
    path: Path,
    config: HermesConfig,
    pairs: list[EvalPair],
    metrics: dict[str, float],
    latency: dict[str, float],
) -> None:
    lines = [
        "# HERMES Evaluation Report",
        "",
        "## Configuration",
        "",
        f"- **Bi-encoder model**: `{config.embed.biencoder_model}`",
        f"- **Cross-encoder model**: `{config.embed.crossencoder_model}`",
        f"- **Retrieval mode**: `{config.search.retrieval_mode}`",
        f"- **Top-K retrieve**: {config.search.top_k_retrieve}",
        f"- **Top-K rerank**: {config.search.top_k_rerank}",
        f"- **Max rerank candidates**: {config.search.max_rerank_candidates}",
        "",
        "## Dataset",
        "",
        f"- **Method**: Auto-generated from code symbols, docstrings, and comments",
        f"- **Number of queries**: {len(pairs)}",
        f"- **Positives per query**: 1",
        "",
        "## Retrieval Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]

    for key, val in sorted(metrics.items()):
        lines.append(f"| {key} | {val:.4f} |")

    lines.extend([
        "",
        "## Latency",
        "",
        "| Stat | ms |",
        "|------|-----|",
        f"| p50 | {latency['p50_ms']} |",
        f"| p95 | {latency['p95_ms']} |",
        f"| mean | {latency['mean_ms']} |",
        "",
        "## Engineering Tradeoffs",
        "",
        "- **Bi-encoder speed vs quality**: Smaller models (MiniLM) are fast on CPU "
        "but may miss nuanced code semantics. Larger models (CodeBERT, BGE) improve "
        "recall but increase indexing time and memory.",
        "- **Cross-encoder precision vs latency**: Reranking with a cross-encoder "
        "significantly improves precision (MRR, nDCG) but adds latency proportional "
        "to the number of candidates. The `max_rerank_candidates` setting controls this tradeoff.",
        "- **Dense vs hybrid retrieval**: Hybrid mode (dense + BM25) can improve recall "
        "for keyword-heavy queries (e.g., exact function names) at the cost of maintaining "
        "a second index and slightly higher query latency.",
        "- **Chunk size**: Larger chunks provide more context but reduce retrieval "
        "granularity. Smaller chunks are more precise but may split logical units.",
        "",
    ])

    path.write_text("\n".join(lines))
