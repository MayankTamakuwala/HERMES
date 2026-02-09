"""HERMES command-line interface."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import click

from hermes.config import load_config
from hermes.logging import setup_logging


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
@click.option("--log-json", is_flag=True, help="Emit JSON-formatted logs")
@click.pass_context
def cli(ctx, log_level: str, log_json: bool):
    """HERMES: Hybrid Embedding Retrieval with Multi-stage Evaluation & Scoring."""
    setup_logging(level=log_level, json_output=log_json)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["log_json"] = log_json


@cli.command()
@click.option("--repo", required=True, type=click.Path(exists=True), help="Path to repository")
@click.option("--out", default="artifacts", type=click.Path(), help="Output directory for artifacts")
def index(repo: str, out: str):
    """Index a repository: scan, chunk, embed, and build FAISS index."""
    from hermes.index.build import build_index

    config = load_config(artifacts_dir=Path(out))
    summary = build_index(Path(repo), config)

    click.echo("\nIndexing complete:")
    for k, v in summary.items():
        click.echo(f"  {k}: {v}")


def _start_api(artifacts: str, host: str, port: int, reload: bool):
    """Start the HERMES API server (uvicorn)."""
    import uvicorn

    from hermes.api.main import create_app

    artifacts_path = Path(artifacts)
    if not artifacts_path.exists():
        click.echo(f"Error: Artifacts directory '{artifacts}' does not exist.", err=True)
        sys.exit(1)

    config = load_config(artifacts_dir=artifacts_path)
    app = create_app(config)
    uvicorn.run(app, host=host, port=port, reload=reload)


@cli.group(invoke_without_command=True)
@click.option("--artifacts", default="artifacts", type=click.Path(), help="Artifacts directory")
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", default=8000, type=int, help="Bind port")
@click.option("--reload", is_flag=True, help="Enable auto-reload (dev only)")
@click.pass_context
def serve(ctx, artifacts: str, host: str, port: int, reload: bool):
    """Start the HERMES query API server."""
    ctx.ensure_object(dict)
    ctx.obj["serve_opts"] = {
        "artifacts": artifacts,
        "host": host,
        "port": port,
        "reload": reload,
    }
    if ctx.invoked_subcommand is None:
        _start_api(artifacts, host, port, reload)


@serve.command()
@click.option("--ui-port", default=3000, type=int, help="Next.js dev server port")
@click.pass_context
def ui(ctx, ui_port: int):
    """Start HERMES API server and Next.js web UI concurrently."""
    import subprocess

    opts = ctx.obj["serve_opts"]
    artifacts_path = Path(opts["artifacts"])
    artifacts_path.mkdir(parents=True, exist_ok=True)

    web_dir = Path(__file__).resolve().parent.parent.parent / "web"
    if not web_dir.is_dir():
        click.echo(f"Error: web directory not found at {web_dir}", err=True)
        sys.exit(1)

    click.echo(f"Starting Next.js dev server on port {ui_port}...")
    next_proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "-p", str(ui_port)],
        cwd=str(web_dir),
    )

    click.echo(f"\n  API server:  http://{opts['host']}:{opts['port']}")
    click.echo(f"  Web UI:      http://localhost:{ui_port}\n")

    try:
        _start_api(
            opts["artifacts"], opts["host"], opts["port"], opts["reload"],
        )
    finally:
        click.echo("\nShutting down Next.js dev server...")
        next_proc.terminate()
        try:
            next_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            next_proc.kill()


@cli.command("eval")
@click.option("--artifacts", default="artifacts", type=click.Path(exists=True), help="Artifacts directory")
@click.option("--repo", default=None, type=click.Path(exists=True), help="Repository path (for dataset generation)")
@click.option("--out", default="reports", type=click.Path(), help="Output directory for reports")
@click.option("--dataset", default=None, type=click.Path(), help="Path to pre-built eval dataset JSON")
@click.option("--max-queries", default=200, type=int, help="Max queries to generate/evaluate")
def eval_cmd(artifacts: str, repo: str | None, out: str, dataset: str | None, max_queries: int):
    """Run evaluation and generate a metrics report."""
    from hermes.eval.run_eval import run_evaluation

    config = load_config(artifacts_dir=Path(artifacts))
    ds_path = Path(dataset) if dataset else None

    report = run_evaluation(
        config,
        repo_path=Path(repo) if repo else None,
        output_dir=Path(out),
        eval_dataset_path=ds_path,
        max_queries=max_queries,
    )
    click.echo(f"\nReport written to: {report}")


@cli.command()
@click.option("--artifacts", default="artifacts", type=click.Path(exists=True), help="Artifacts directory")
@click.option("--queries", required=True, type=click.Path(exists=True), help="JSONL file with queries")
@click.option("--top-k", default=10, type=int, help="Top-K results per query")
def bench(artifacts: str, queries: str, top_k: int):
    """Run latency benchmarks against indexed artifacts."""
    from hermes.search.pipeline import SearchPipeline
    from hermes.search.schemas import SearchRequest

    config = load_config(artifacts_dir=Path(artifacts))
    pipeline = SearchPipeline(config)

    # Load queries
    query_list: list[str] = []
    with open(queries) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            query_list.append(obj.get("query", obj.get("text", "")))

    if not query_list:
        click.echo("No queries found in file")
        sys.exit(1)

    click.echo(f"Benchmarking {len(query_list)} queries...")

    latencies: list[float] = []
    embed_times: list[float] = []
    faiss_times: list[float] = []
    rerank_times: list[float] = []

    for q in query_list:
        req = SearchRequest(query=q, top_k_retrieve=config.search.top_k_retrieve, top_k_rerank=top_k)
        t0 = time.perf_counter()
        resp = pipeline.search(req)
        total = (time.perf_counter() - t0) * 1000
        latencies.append(total)
        embed_times.append(resp.timings_ms.get("embed_query_ms", 0))
        faiss_times.append(resp.timings_ms.get("retrieval_ms", 0))
        rerank_times.append(resp.timings_ms.get("rerank_ms", 0))

    import tracemalloc
    tracemalloc.start()

    req = SearchRequest(query=query_list[0], top_k_retrieve=config.search.top_k_retrieve, top_k_rerank=top_k)
    pipeline.search(req)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    def _percentile(data, p):
        data_sorted = sorted(data)
        idx = int(len(data_sorted) * p / 100)
        return data_sorted[min(idx, len(data_sorted) - 1)]

    click.echo(f"\n{'Metric':<25} {'p50':>10} {'p95':>10}")
    click.echo("-" * 47)
    click.echo(f"{'Total (ms)':<25} {_percentile(latencies, 50):>10.1f} {_percentile(latencies, 95):>10.1f}")
    click.echo(f"{'Embed query (ms)':<25} {_percentile(embed_times, 50):>10.1f} {_percentile(embed_times, 95):>10.1f}")
    click.echo(f"{'FAISS search (ms)':<25} {_percentile(faiss_times, 50):>10.1f} {_percentile(faiss_times, 95):>10.1f}")
    click.echo(f"{'Rerank (ms)':<25} {_percentile(rerank_times, 50):>10.1f} {_percentile(rerank_times, 95):>10.1f}")
    click.echo(f"\nMemory (current/peak): {current / 1024 / 1024:.1f} MB / {peak / 1024 / 1024:.1f} MB")
