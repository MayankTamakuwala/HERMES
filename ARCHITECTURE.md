# HERMES Architecture

**Hybrid Embedding Retrieval with Multi-stage Evaluation & Scoring**

This document describes the internal architecture of HERMES — a semantic code search system that combines bi-encoder retrieval (dense + sparse) with cross-encoder reranking to deliver high-precision results with low latency.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      User Interfaces                             │
├──────────────────┬───────────────────┬───────────────────────────┤
│   CLI (Click)    │  Next.js Web UI   │    cURL / HTTP clients    │
│                  │  (React 19)       │                           │
│  hermes index    │  /  Search page   │  POST /search             │
│  hermes serve    │  /index-repo      │  GET  /stats              │
│  hermes serve ui │  /stats           │  POST /index              │
│  hermes eval     │  /settings        │  GET  /health             │
│  hermes bench    │                   │                           │
└──────────────────┴───────────────────┴───────────────────────────┘
                              │
┌─────────────────────────────V────────────────────────────────────┐
│                      API Layer (FastAPI)                         │
├──────────┬───────────┬────────────┬──────────┬───────────────────┤
│ /search  │ /stats    │ /index     │ /health  │ /index/check      │
│          │           │ /index/    │          │ /reload-index     │
│          │           │   status   │          │                   │
└──────────┴───────────┴────────────┴──────────┴───────────────────┘
                              │
┌─────────────────────────────V────────────────────────────────────┐
│                      Search Pipeline                             │
├────────────────┬─────────────────┬──────────────────┬────────────┤
│  Bi-Encoder    │  FAISS Index    │  BM25 Index      │  Cross-    │
│  (embed query) │  (dense search) │  (sparse search) │  Encoder   │
│                │                 │                  │  (rerank)  │
├────────────────┴────────┬────────┴──────────────────┴────────────┤
│                         │                                        │
│  RRF Fusion       Embedding Cache       Metadata Store (SQLite)  │
└─────────────────────────┴────────────────────────────────────────┘
                              │
┌─────────────────────────────V────────────────────────────────────┐
│                      Indexing Pipeline                           │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│  Repo        │  Language-   │  Bi-Encoder  │  Index Builders     │
│  Scanner     │  Aware       │  (embed      │  (FAISS + BM25 +    │
│  (ingest)    │  Chunker     │   chunks)    │   SQLite)           │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
                              │
┌─────────────────────────────V────────────────────────────────────┐
│                      Foundation                                  │
├─────────────────┬──────────────────┬─────────────────────────────┤
│  Configuration  │  Structured      │  Evaluation Framework       │
│  (pydantic-     │  Logging         │  (dataset gen + metrics)    │
│   settings)     │  (structlog)     │                             │
└─────────────────┴──────────────────┴─────────────────────────────┘
                              │
┌─────────────────────────────V────────────────────────────────────┐
│                      External Dependencies                       │
├──────────┬───────────┬────────────┬──────────┬───────┬───────────┤
│  PyTorch │  sentence │  FAISS     │  FastAPI │ Click │  rank-    │
│          │-transform │  (faiss-   │  Uvicorn │       │  bm25     │
│          │  -ers     │   cpu)     │          │       │           │
└──────────┴───────────┴────────────┴──────────┴───────┴───────────┘
```

---

## Ways to Use HERMES

HERMES can be used in **four distinct modes**, each building on the layers above:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   Mode 1: CLI-Only                                                  │
│   ─────────────────                                                 │
│   hermes index --repo ./myproject                                   │
│   hermes bench --artifacts ./artifacts --queries queries.jsonl      │
│   hermes eval  --artifacts ./artifacts                              │
│                                                                     │
│   Best for: CI pipelines, scripted workflows, one-off analysis      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Mode 2: API Server                                                │
│   ──────────────────                                                │
│   hermes serve --artifacts ./artifacts --port 8000                  │
│                                                                     │
│   Exposes REST API at :8000                                         │
│   Integrate with IDE plugins, chat assistants, custom frontends     │
│                                                                     │
│   Best for: production deployments, programmatic integration        │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Mode 3: Full-Stack (API + Web UI)                                 │
│   ─────────────────────────────────                                 │
│   hermes serve ui --artifacts ./artifacts                           │
│                                                                     │
│   Starts API (:8000) + Next.js dev server (:3000) concurrently      │
│   Auto-creates artifacts dir if missing                             │
│   Shows welcome screen if no index exists yet                       │
│                                                                     │
│   Best for: local development, demos, team onboarding               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Mode 4: Library / Programmatic                                    │
│   ──────────────────────────────                                    │
│   from hermes.config import load_config                             │
│   from hermes.search.pipeline import SearchPipeline                 │
│   from hermes.search.schemas import SearchRequest                   │
│                                                                     │
│   config = load_config(artifacts_dir=Path("./artifacts"))           │
│   pipeline = SearchPipeline(config)                                 │
│   results = pipeline.search(SearchRequest(query="parse JSON"))      │
│                                                                     │
│   Best for: embedding into larger applications, custom pipelines    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Two-Plane Architecture

HERMES separates concerns into an **offline plane** (indexing) and an **online plane** (serving):

```
                    OFFLINE PLANE                              ONLINE PLANE
              (run once per repo update)                  (runs on every query)

  ┌───────────────┐                              ┌───────────────────────────┐
  │  Repository   │                              │    User Query             │
  └───────┬───────┘                              └─────────────┬─────────────┘
          │                                                    │
          V                                                    V
  ┌───────────────┐                              ┌───────────────────────────┐
  │ Repo Scanner  │  Discover files,             │  Bi-Encoder               │
  │ (ingest/)     │  detect languages            │  Embed query (cached)     │
  └───────┬───────┘                              └─────────────┬─────────────┘
          │                                                    │
          V                                           ┌────────┴────────┐
  ┌───────────────┐                                   │                 │
  │ Chunker       │  Split into semantic              V                 V
  │ (chunking/)   │  code blocks              ┌────────────┐   ┌────────────┐
  └───────┬───────┘                           │   FAISS     │   │   BM25     │
          │                                   │  (dense)    │   │  (sparse)  │
          V                                   └──────┬──────┘   └──────┬─────┘
  ┌───────────────┐                                  │                 │
  │ Bi-Encoder    │  Embed all chunks                └────────┬────────┘
  │ (embed/)      │  in batches                               │
  └───────┬───────┘                                           V
          │                                          ┌─────────────────┐
          V                                          │   RRF Fusion    │
  ┌───────────────────────────────┐                  │   (hybrid mode) │
  │  Build & Save Artifacts       │                  └────────┬────────┘
  │                               │                           │
  │  artifacts/                   │                           V
  │  ├── faiss.index              │                 ┌─────────────────┐
  │  ├── sparse_index.json        │                 │  Cross-Encoder  │
  │  ├── metadata.db              │                 │  Rerank top-K   │
  │  └── embeddings.npy           │                 └────────┬────────┘
  └───────────────────────────────┘                          │
                                                             V
                                                    ┌─────────────────┐
                                                    │  Ranked Results │
                                                    │  + Timings      │
                                                    └─────────────────┘
```

---

## Module Reference

### Source Layout

```
src/hermes/
├── cli.py                      # CLI entry point
├── config.py                   # Pydantic-settings configuration
├── logging.py                  # Structured logging (structlog)
│
├── ingest/                     # Repository scanning
│   ├── repo_scanner.py         #   File discovery + filtering
│   └── language_detect.py      #   Extension → language mapping
│
├── chunking/                   # Language-aware code splitting
│   ├── base.py                 #   Chunk dataclass + ChunkerRegistry
│   ├── python_chunker.py       #   AST-based Python chunking
│   ├── js_chunker.py           #   Regex-based JS/TS chunking
│   └── heuristic_chunker.py    #   Line-based fallback chunker
│
├── embed/                      # Neural embedding models
│   ├── biencoder.py            #   SentenceTransformer wrapper
│   ├── crossencoder.py         #   Cross-encoder reranker
│   └── cache.py                #   LRU query embedding cache
│
├── index/                      # Index building + storage
│   ├── build.py                #   Full indexing orchestration
│   ├── faiss_index.py          #   FAISS vector index (Flat / IVF)
│   ├── sparse_index.py         #   BM25 sparse keyword index
│   └── metadata_store.py       #   SQLite chunk metadata store
│
├── search/                     # Query-time pipeline
│   ├── pipeline.py             #   Multi-stage search orchestration
│   ├── fusion.py               #   Reciprocal Rank Fusion (RRF)
│   └── schemas.py              #   Pydantic request/response models
│
├── api/                        # FastAPI REST service
│   ├── main.py                 #   App factory + lifespan management
│   └── routes.py               #   API endpoint definitions
│
└── eval/                       # Evaluation framework
    ├── dataset.py              #   Auto-generate eval query pairs
    ├── metrics.py              #   Recall@K, MRR@K, nDCG@K
    └── run_eval.py             #   Evaluation runner + report gen
```

### Web Frontend Layout

```
web/
├── package.json                # Next.js 16, React 19, Tailwind v4
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with IndexGuard
│   │   ├── page.tsx            # Search page (main interface)
│   │   ├── index-repo/
│   │   │   └── page.tsx        # Repository indexing page
│   │   ├── stats/
│   │   │   └── page.tsx        # Statistics dashboard
│   │   └── settings/
│   │       └── page.tsx        # Settings page
│   ├── components/
│   │   ├── layout/
│   │   │   ├── sidebar.tsx     # Navigation sidebar
│   │   │   └── header.tsx      # Top header bar
│   │   ├── search/
│   │   │   ├── search-bar.tsx  # Query input
│   │   │   ├── filters-panel.tsx # Retrieval mode, top-k, filters
│   │   │   ├── result-card.tsx # Code result with scores
│   │   │   └── timing-bar.tsx  # Visual timing breakdown
│   │   ├── index/
│   │   │   ├── index-guard.tsx # Routes to welcome if no index
│   │   │   ├── index-panel.tsx # Indexing controls + status
│   │   │   └── welcome-screen.tsx # First-run setup screen
│   │   ├── stats/
│   │   │   └── stats-cards.tsx # Dashboard metric cards
│   │   └── ui/                 # shadcn/ui primitives
│   └── lib/
│       ├── api.ts              # Typed API client
│       └── utils.ts            # Utility helpers (cn)
```

---

## Module Details

### ingest/ — Repository Scanning

Walks a repository tree and discovers indexable source files.

- **repo_scanner.py**: Recursive file discovery. Skips `.git`, `node_modules`, `venv`, `build`, `dist`, `__pycache__`, and other non-source directories. Enforces a 1 MB max file size. Returns `ScannedFile` objects with path, language, and size.
- **language_detect.py**: Maps 40+ file extensions to language identifiers. Differentiates code files from config/docs.

### chunking/ — Language-Aware Code Splitting

Splits source files into semantically meaningful blocks (functions, classes, or fixed-size windows).

- **base.py**: Defines the `Chunk` dataclass (file_path, language, start_line, end_line, code_text, symbol_name) and `ChunkerRegistry` for language-specific dispatch.
- **python_chunker.py**: Uses Python's `ast` module to extract top-level functions, classes, and async functions. Falls back to heuristic on syntax errors. Splits oversized blocks with configurable overlap.
- **js_chunker.py**: Regex-based detection of function/class boundaries for JavaScript and TypeScript.
- **heuristic_chunker.py**: Generic line-based windowing with overlap. Attempts to break at structural hints (`def`, `fn`, `class`, `func`). Used for Rust, Go, Java, C/C++, Ruby, PHP, and any unsupported language.

### embed/ — Neural Embedding Models

Handles all model inference for both indexing and query time.

- **biencoder.py**: Wraps `sentence-transformers.SentenceTransformer`. Default model: `all-MiniLM-L6-v2` (22M params, 384-dim). Batch encodes chunks during indexing. Single-query encode at search time (with caching).
- **crossencoder.py**: Wraps `sentence-transformers.CrossEncoder`. Default: `cross-encoder/ms-marco-MiniLM-L-6-v2`. Scores (query, passage) pairs for reranking. Called only on top-K candidates.
- **cache.py**: Thread-safe LRU cache (OrderedDict) for query embeddings. SHA256 key hashing. Tracks hit/miss rates exposed via `/stats`.

### index/ — Index Building & Storage

Builds and persists the search artifacts.

- **build.py**: Orchestrates the full pipeline: scan → chunk → embed → build indexes → save to `artifacts/`. Returns a summary dict with timing and counts.
- **faiss_index.py**: `IndexFlatIP` for <100k vectors (exact inner product), `IndexIVFFlat` for larger corpora (configurable via `HERMES_INDEX_FAISS_USE_IVF`). Save/load from disk.
- **sparse_index.py**: BM25Okapi from `rank-bm25`. Custom tokenizer that splits on non-alphanumeric characters and handles camelCase/snake_case. Serialized as JSON.
- **metadata_store.py**: SQLite database (`metadata.db`) in WAL mode. Stores chunk text, file paths, languages, line ranges, and symbol names. Indexed on file_path and language.

### search/ — Query Pipeline

Multi-stage search orchestration at query time.

- **pipeline.py**: `SearchPipeline` loads all artifacts and models on init. The `search()` method runs: embed query → retrieve (dense/sparse/hybrid) → apply filters → rerank with cross-encoder (with timeout fallback) → build results. Uses a `ThreadPoolExecutor` (2 workers) for reranking. Supports hot reload without server restart.
- **fusion.py**: Reciprocal Rank Fusion implementation. Merges multiple ranked lists using: `score = Σ 1/(k + rank + 1)` where `k` is a configurable constant (default 60).
- **schemas.py**: Pydantic models for `SearchRequest`, `SearchResponse`, `SearchResultItem`, and `StatsResponse`. Defines all API contracts.

### api/ — FastAPI Service

REST API layer that wraps the search pipeline.

- **main.py**: Application factory (`create_app`). Lifespan handler loads `SearchPipeline` on startup — gracefully handles missing index by setting `pipeline = None`. CORS configured for `localhost:3000`.
- **routes.py**: Endpoint definitions. `_require_pipeline()` helper returns 400 if no index is loaded. Endpoints: `/search`, `/stats`, `/health`, `/index`, `/index/status`, `/index/check`, `/reload-index`.

### eval/ — Evaluation Framework

Automated evaluation and metrics reporting.

- **dataset.py**: Auto-generates evaluation query-chunk pairs from code. Strategies: extract Python docstrings, use leading comments, convert symbol names to natural language (e.g., `calculate_bmi` → "How does calculate bmi work?").
- **metrics.py**: Computes `recall_at_k`, `mrr_at_k`, `ndcg_at_k`. Aggregates over query sets for Recall@5/10/50, MRR@10, nDCG@10.
- **run_eval.py**: Runs full evaluation: generate/load dataset → execute queries → compute metrics → write markdown report with latency breakdowns.

---

## Data Flow

### Indexing Data Flow

```
Repository on disk
      │
      V
ScannedFile[]  <-- repo_scanner.scan_repository()
      │
      V
Chunk[]        <-- chunker.chunk_file() per file
      │
      ├──> BiEncoder.encode_batch() --> embeddings.npy + faiss.index
      │
      ├──> SparseIndex.build()      --> sparse_index.json
      │
      └──> MetadataStore.insert()   --> metadata.db
```

### Search Data Flow

```
Query string
      │
      V
Query vector   <-- BiEncoder.encode() (cached)
      │
      ├──> FaissIndex.search()     --> dense_ids + scores
      │
      ├──> SparseIndex.search()    --> sparse_ids + scores
      │
      V
Fused IDs      <-- reciprocal_rank_fusion()  (hybrid mode)
      │
      V
Filtered IDs   <-- apply language/path filters
      │
      V
Reranked IDs   <-- CrossEncoder.predict()  (with timeout)
      │
      V
SearchResponse <-- MetadataStore.get_chunks_by_ids() + scores + timings
```

---

## API Endpoints

| Method | Path             | Description                                   | Requires Index |
|--------|------------------|-----------------------------------------------|:--------------:|
| GET    | `/health`        | Liveness check                                | No             |
| GET    | `/index/check`   | Returns `{"has_index": true/false}`           | No             |
| GET    | `/index/status`  | Indexing job status (idle/indexing/done/error)| No             |
| POST   | `/index`         | Start async indexing of a repository          | No             |
| POST   | `/search`        | Search the indexed codebase                   | Yes            |
| GET    | `/stats`         | Index stats, model info, cache hit rates      | Yes            |
| POST   | `/reload-index`  | Hot-reload index from disk                    | Yes            |

Endpoints marked "Requires Index" return HTTP 400 with `"No index loaded. Please index a repository first."` when no index is available.

---

## CLI Commands

| Command              | Description                                        |
|----------------------|----------------------------------------------------|
| `hermes index`       | Scan, chunk, embed, and build FAISS/BM25 indexes   |
| `hermes serve`       | Start the API server only                          |
| `hermes serve ui`    | Start API server + Next.js web UI concurrently     |
| `hermes eval`        | Run evaluation and generate metrics report         |
| `hermes bench`       | Run latency benchmarks (p50/p95)                   |

### `hermes serve ui` Behavior

- Creates the artifacts directory if it doesn't exist
- Launches the Next.js dev server as a subprocess (`npm run dev`)
- Starts uvicorn in the main thread
- On shutdown (Ctrl+C), terminates the Next.js process gracefully
- If no index exists, the API starts with `pipeline = None` and the web UI shows a welcome screen prompting the user to index a repository

---

## Index-First Welcome Flow

When the web UI loads without an existing index:

```
Browser loads localhost:3000
      │
      V
IndexGuard calls GET /index/check
      │
      ├── has_index: true  -->  Normal UI (sidebar + search page)
      │
      └── has_index: false -->  WelcomeScreen
                                      │
                                      V
                              User enters repo path
                              Clicks "Start Indexing"
                                      │
                                      V
                              POST /index (starts background thread)
                              Polls GET /index/status every 2s
                                      │
                                      V
                              Indexing completes (state: "done")
                              Pipeline created from new artifacts
                                      │
                                      V
                              Re-check GET /index/check → true
                              Transition to normal UI
```

---

## Configuration

All settings via environment variables with `HERMES_` prefix. Managed by pydantic-settings.

### Key Configuration Groups

| Group      | Env Prefix               | Examples                                      |
|------------|--------------------------|-----------------------------------------------|
| Chunking   | `HERMES_CHUNK_`          | `MAX_CHARS=1500`, `OVERLAP_LINES=3`           |
| Embedding  | `HERMES_EMBED_`          | `BIENCODER_MODEL=all-MiniLM-L6-v2`            |
| Index      | `HERMES_INDEX_`          | `FAISS_USE_IVF=false`, `FAISS_NPROBE=10`      |
| Search     | `HERMES_SEARCH_`         | `RETRIEVAL_MODE=hybrid`, `TOP_K_RETRIEVE=100` |
| Logging    | `HERMES_LOG_`            | `LEVEL=INFO`, `JSON=false`                    |

---

## Technology Stack

### Backend (Python 3.11+)

| Component         | Library                             | Purpose                        |
|-------------------|-------------------------------------|--------------------------------|
| ML Models         | sentence-transformers, PyTorch      | Bi-encoder + cross-encoder     |
| Dense Index       | faiss-cpu                           | Vector similarity search       |
| Sparse Index      | rank-bm25                           | BM25 keyword search            |
| API Server        | FastAPI + Uvicorn                   | REST API                       |
| Configuration     | pydantic-settings                   | Typed config with env vars     |
| CLI               | Click                               | Command-line interface         |
| Logging           | structlog                           | Structured logging             |
| Metadata Store    | SQLite (stdlib)                     | Chunk metadata persistence     |

### Frontend

| Component         | Library                             | Purpose                        |
|-------------------|-------------------------------------|--------------------------------|
| Framework         | Next.js 16                          | React framework with SSR       |
| UI Library        | React 19                            | Component rendering            |
| Styling           | Tailwind CSS v4                     | Utility-first CSS              |
| Components        | shadcn/ui + Radix UI                | Accessible UI primitives       |
| Icons             | Lucide React                        | Icon set                       |

### Dev & Test

| Tool              | Purpose                             |
|-------------------|-------------------------------------|
| pytest            | Unit + integration tests            |
| httpx             | Async HTTP test client              |
| ruff              | Linting + formatting                |
| ESLint            | Frontend linting                    |
| TypeScript        | Frontend type safety                |
