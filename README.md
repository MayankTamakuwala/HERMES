# HERMES: **Hybrid Embedding Retrieval with Multi-stage Evaluation & Scoring**

A production-grade semantic code search system that takes a natural-language query and returns the most relevant code chunks with high precision, low latency, and auditable behavior.

## The Problem

Modern engineering orgs waste real time searching internal codebases:

- *"Where is OAuth token refresh implemented?"*
- *"How do we parse protobuf X?"*
- *"Where do we validate invoice totals?"*

**Keyword search fails** when terminology differs (e.g., searching "refresh token" won't find code that calls it "renew session"). **Naive embedding search** often returns "nearby" but wrong functions because a single retrieval stage lacks the precision to distinguish semantically close but functionally different code.

HERMES solves this with a **two-stage approach**: fast approximate retrieval to narrow down candidates, followed by precise reranking to surface the right result.

### Who is this for?

- **Developer productivity teams** building internal search tools
- **Platform teams** integrating code search into IDE plugins or chat assistants
- **Internal tooling engineers** powering code discovery in developer portals

## Why Bi-Encoder + Cross-Encoder?

| Stage | Model Type | Speed | Quality | Purpose |
|-------|-----------|-------|---------|---------|
| Retrieval | Bi-encoder | Fast (ms) | Good | Narrow 100k chunks to top 100 |
| Reranking | Cross-encoder | Slower (100ms) | Excellent | Refine top 100 to top 10 |

- **Bi-encoders** embed queries and code independently, enabling pre-computation and FAISS indexing for sub-millisecond search over millions of vectors.
- **Cross-encoders** jointly attend to query+code pairs, producing more accurate relevance scores but requiring inference per pair -- impractical for full-corpus search, ideal for reranking a short list.

Neither stage alone is sufficient. The bi-encoder casts a wide net quickly; the cross-encoder picks the best fish. Together they achieve both speed and precision.

## Architecture

```
|----------------------------------------------------------|
│  STEP 1: INDEXING (run once, before any search)          │
│  Command: hermes index --repo /path/to/repo              │
│                                                          │
│  Repository --> Scanner --> Chunker ──┬──> Embedder      │
│                                      │        │          │
│                                      │        V          │
│                                      │    FAISS Index    │
│                                      │    BM25 Index     │
│                                      │        │          │
│                                      V        V          │
│                                  SQLite    artifacts/    │
│                                  Store        │          │
│                                    │          │          │
│                                    V          V          │
│                                   artifacts/             │
|__________________________________________________________|

|----------------------------------------------------------|
│  STEP 2: SEARCHING (runs on every query)                 │
│  Command: hermes serve --artifacts ./artifacts           │
│                                                          │
│  Query --> Embed query (cached)                          │
│               │                                          │
│               V                                          │
│        ___________________                               │
│        |                 |                               │
│        V                 V                               │
│   Dense search     Sparse search                         │
│     (FAISS)             (BM25)                           │
│        │                 │                               │
│        V                 V                               │
│        |___ RRF Fusion __|                               │
│                │                                         │
│                V                                         │
│         Cross-encoder rerank                             │
│         (batch scoring + timeout)                        │
│                │                                         │
│                V                                         │
│         FastAPI Response                                 │
│         (scores + explainability)                        │
|__________________________________________________________|
```

## Quickstart

### Install

```bash
# Clone and install
git clone <repo-url> && cd HERMES
pip install -e ".[dev]"
```

### Index a Repository

```bash
hermes index --repo /path/to/your/project --out ./artifacts
```

### Start the Query Server

```bash
# API only
hermes serve --artifacts ./artifacts --port 8000

# API + Web UI (recommended for local development)
hermes serve ui --artifacts ./artifacts
# → API at http://0.0.0.0:8000
# → Web UI at http://localhost:3000
```

If no index exists yet, the web UI will show a welcome screen prompting you to index a repository before searching.

### Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "read file from disk", "top_k_rerank": 5}'
```

### Run Evaluation

```bash
hermes eval --artifacts ./artifacts --out ./reports
# Produces reports/eval_report.md
```

### Run Benchmarks

```bash
# Prepare a queries file (JSONL with "query" field per line)
echo '{"query": "parse JSON"}' > queries.jsonl
echo '{"query": "database connection"}' >> queries.jsonl

hermes bench --artifacts ./artifacts --queries queries.jsonl
```

### Run Tests

```bash
pytest
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search` | Search the indexed codebase |
| GET | `/health` | Health check |
| GET | `/stats` | Index stats, model info, cache hit rates |
| POST | `/reload-index` | Reload index from disk without restart |
| GET | `/index/check` | Check if an index is loaded (`{"has_index": bool}`) |
| POST | `/index` | Start async indexing of a repository |
| GET | `/index/status` | Poll indexing progress (idle/indexing/done/error) |

### POST /search

**Request:**
```json
{
  "query": "read a configuration file",
  "top_k_retrieve": 100,
  "top_k_rerank": 10,
  "retrieval_mode": "dense",
  "filter_language": "python",
  "filter_path_prefix": "src/",
  "return_snippets": true
}
```

**Response:**
```json
{
  "request_id": "a1b2c3d4e5f6",
  "query": "read a configuration file",
  "retrieval_mode": "dense",
  "results": [
    {
      "chunk_id": 42,
      "file_path": "src/config.py",
      "language": "python",
      "start_line": 10,
      "end_line": 25,
      "symbol_name": "load_config",
      "code_snippet": "def load_config(path)...",
      "retrieval_rank": 3,
      "retrieval_score": 0.8234,
      "rerank_score": 0.9512,
      "final_rank": 1
    }
  ],
  "timings_ms": {
    "embed_query_ms": 12.5,
    "retrieval_ms": 1.2,
    "rerank_ms": 85.3,
    "total_ms": 99.1
  },
  "rerank_skipped": false,
  "total_candidates": 100
}
```

## Configuration

All settings are configurable via environment variables or programmatically.

### Models

| Setting | Env Variable | Default | Notes |
|---------|-------------|---------|-------|
| Bi-encoder | `HERMES_EMBED_BIENCODER_MODEL` | `all-MiniLM-L6-v2` | 80MB, fast on CPU |
| Cross-encoder | `HERMES_EMBED_CROSSENCODER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | 80MB, good quality/latency |

**Model selection rationale:**
- `all-MiniLM-L6-v2`: 22M parameters, 384-dim embeddings, ~14ms/query on CPU. Trained on 1B+ sentence pairs. Provides a strong baseline for semantic similarity including code/NL matching. For better code-specific performance, consider `BAAI/bge-small-en-v1.5` or `flax-sentence-embeddings/st-codesearch-distilroberta-base`.
- `cross-encoder/ms-marco-MiniLM-L-6-v2`: 22M parameters, trained on MS MARCO passage ranking. Effective for query-passage relevance scoring on CPU. For code-specific reranking, consider `cross-encoder/ms-marco-TinyBERT-L-2-v2` (faster) or `cross-encoder/ms-marco-MiniLM-L-12-v2` (more accurate).

### Chunking

| Setting | Env Variable | Default |
|---------|-------------|---------|
| Max chars per chunk | `HERMES_CHUNK_MAX_CHARS` | 1500 |
| Overlap lines | `HERMES_CHUNK_OVERLAP_LINES` | 3 |
| Min chunk chars | `HERMES_CHUNK_MIN_CHARS` | 50 |

### Search

| Setting | Env Variable | Default |
|---------|-------------|---------|
| Retrieval top-K | `HERMES_SEARCH_TOP_K_RETRIEVE` | 100 |
| Rerank top-K | `HERMES_SEARCH_TOP_K_RERANK` | 10 |
| Max rerank candidates | `HERMES_SEARCH_MAX_RERANK_CANDIDATES` | 50 |
| Rerank timeout (sec) | `HERMES_SEARCH_RERANK_TIMEOUT_SECONDS` | 10.0 |
| Retrieval mode | `HERMES_SEARCH_RETRIEVAL_MODE` | `hybrid` |

### Retrieval Modes

HERMES supports three retrieval strategies, each with different strengths:

#### Dense (`dense`)

**Searches by meaning.** The query and every code chunk are converted into numerical vectors (embeddings) by the bi-encoder. FAISS finds the chunks whose vectors are closest to the query vector using cosine similarity.

- Best for natural-language queries: *"how to read a configuration file"*
- Understands intent -- finds `open()` and `load()` even if the words "read" and "file" don't appear
- May miss exact identifiers: searching `calculateBMI` might return `compute_weight_ratio` instead

#### Sparse (`sparse`)

**Searches by keywords.** Uses BM25 (the same algorithm behind Elasticsearch) to rank chunks by how often query terms appear in them, adjusted for chunk length.

- Best for exact names: *"calculateBMI"*, *"AuthTokenRefreshService"*
- Fast, simple word matching
- Misses semantic connections: *"how to read a file"* won't match code using `open()` and `load()`

#### Hybrid (`hybrid`)

**Runs both dense and sparse, then merges results.** Combines the two ranked lists using Reciprocal Rank Fusion (RRF), then reranks the merged list with the cross-encoder.

```
Query: "calculateBMI function"
      │
      |- Dense:  [compute_health_score, calculateBMI, get_weight_ratio]
      │
      |- Sparse: [calculateBMI, bmi_validator, bmi_test]
      │
      |-> RRF Fusion
      [calculateBMI, compute_health_score, bmi_validator, ...]
      │
      |-> Cross-encoder rerank
      Final results
```

- Best overall recall -- catches what either method alone would miss
- Slightly slower (two searches instead of one)
- Recommended for production use

| Mode | How it searches | Best for | Tradeoff |
|------|----------------|----------|----------|
| `dense` | Meaning/semantics | Natural-language queries | Fastest, may miss exact names |
| `sparse` | Keyword matching | Exact identifiers | Fast, misses semantic matches |
| `hybrid` | Both combined | Everything | Best quality, slightly slower |

Set the mode via environment variable or `.env` file:
```bash
HERMES_SEARCH_RETRIEVAL_MODE=hybrid
```

## Supported Languages

AST-based chunking: **Python**, **JavaScript/TypeScript**

Heuristic chunking (fallback): **Java**, **Go**, **Rust**, **C/C++**, **Ruby**, **PHP**, and more

## Evaluation & Benchmarking

### Evaluation

The evaluation pipeline auto-generates query-relevant chunk pairs using heuristics:
1. Python docstrings become queries
2. Leading comments become queries
3. Symbol names are converted to natural-language questions

```bash
hermes eval --artifacts ./artifacts --out ./reports --max-queries 200
```

Output: `reports/eval_report.md` with Recall@K, MRR@10, nDCG@10, and latency breakdowns.

### Benchmarking

```bash
hermes bench --artifacts ./artifacts --queries queries.jsonl --top-k 10
```

Reports p50/p95 latency for: query embedding, FAISS search, reranking, and total.

## Troubleshooting

### FAISS installation issues
```bash
# macOS / Linux
pip install faiss-cpu

# If you have issues, try conda:
conda install -c conda-forge faiss-cpu
```

### Out of memory during indexing
- Reduce `HERMES_EMBED_BIENCODER_BATCH_SIZE` (default: 64)
- For very large repos (>200k LOC), enable IVF: `HERMES_INDEX_FAISS_USE_IVF=true`

### Slow reranking
- Reduce `HERMES_SEARCH_MAX_RERANK_CANDIDATES` (default: 50)
- The system automatically falls back to retrieval-only results if reranking exceeds the timeout
- Consider a smaller cross-encoder model

### Model download
Models are downloaded automatically from Hugging Face on first use. Set `HF_HOME` to control the cache location.

## Project Structure

```
src/hermes/
├── cli.py                   # CLI entry point (index, serve, serve ui, eval, bench)
├── config.py                # Pydantic-settings configuration
├── logging.py               # Structured logging (structlog)
├── chunking/                # Language-aware code chunking
│   ├── base.py              # Chunk type + registry
│   ├── python_chunker.py    # AST-based Python chunking
│   ├── js_chunker.py        # Heuristic JS/TS chunking
│   └── heuristic_chunker.py # Fallback line-based chunker
├── ingest/                  # Repository scanning
│   ├── repo_scanner.py      # File discovery + filtering
│   └── language_detect.py   # Extension to language mapping
├── embed/                   # Embedding models
│   ├── biencoder.py         # Sentence-transformers bi-encoder
│   ├── crossencoder.py      # Cross-encoder reranker
│   └── cache.py             # LRU embedding cache
├── index/                   # Index building + storage
│   ├── faiss_index.py       # FAISS vector index
│   ├── sparse_index.py      # BM25 sparse index
│   ├── metadata_store.py    # SQLite chunk metadata
│   └── build.py             # Full indexing pipeline
├── search/                  # Query pipeline
│   ├── pipeline.py          # Multi-stage search orchestration
│   ├── fusion.py            # Reciprocal Rank Fusion
│   └── schemas.py           # Request/response Pydantic models
├── api/                     # FastAPI service
│   ├── main.py              # App factory + lifespan
│   └── routes.py            # API endpoints
└── eval/                    # Evaluation framework
    ├── dataset.py           # Auto-generate eval pairs
    ├── metrics.py           # Recall, MRR, nDCG
    └── run_eval.py          # Evaluation runner + report
```
