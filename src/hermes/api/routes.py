"""API route definitions for the HERMES query service."""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hermes.search.schemas import SearchRequest, SearchResponse, StatsResponse


def _require_pipeline(request: Request):
    pipeline = request.app.state.pipeline
    if pipeline is None:
        raise HTTPException(status_code=400, detail="No index loaded. Please index a repository first.")
    return pipeline

router = APIRouter()

# In-memory indexing state
_indexing_lock = threading.Lock()
_indexing_status: dict = {"state": "idle"}


class IndexRequest(BaseModel):
    repo_path: str


@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/")
async def root():
    return await health()


@router.get("/index/check")
async def index_check(request: Request):
    has_index = request.app.state.pipeline is not None
    return {"has_index": has_index}


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request):
    pipeline = _require_pipeline(request)
    return pipeline.search(req)


@router.get("/stats", response_model=StatsResponse)
async def stats(request: Request):
    pipeline = _require_pipeline(request)
    config = request.app.state.config
    cache = pipeline.embedding_cache
    return StatsResponse(
        index_size=pipeline.faiss_index.ntotal,
        n_chunks=pipeline.store.count(),
        biencoder_model=config.embed.biencoder_model,
        crossencoder_model=config.embed.crossencoder_model,
        retrieval_mode=config.search.retrieval_mode,
        cache_hit_rate=round(cache.hit_rate, 4),
        cache_hits=cache.hits,
        cache_misses=cache.misses,
    )


@router.post("/reload-index")
async def reload_index(request: Request):
    pipeline = _require_pipeline(request)
    pipeline.reload()
    return {"status": "reloaded", "n_chunks": pipeline.store.count()}

@router.post("/index")
async def start_indexing(req: IndexRequest, request: Request):
    global _indexing_status

    if not _indexing_lock.acquire(blocking=False):
        return {"status": "error", "message": "Indexing already in progress"}

    repo = Path(req.repo_path)
    if not repo.is_dir():
        _indexing_lock.release()
        return {"status": "error", "message": f"Directory not found: {req.repo_path}"}

    _indexing_status = {"state": "indexing", "repo_path": req.repo_path}
    config = request.app.state.config
    app = request.app

    def _run():
        global _indexing_status
        try:
            from hermes.index.build import build_index
            from hermes.search.pipeline import SearchPipeline

            summary = build_index(repo, config)
            if app.state.pipeline is not None:
                app.state.pipeline.reload()
            else:
                app.state.pipeline = SearchPipeline(config)
            _indexing_status = {"state": "done", "summary": summary}
        except Exception as exc:
            _indexing_status = {"state": "error", "message": str(exc)}
        finally:
            _indexing_lock.release()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"status": "indexing", "message": f"Indexing started for {req.repo_path}"}

@router.get("/index/status")
async def index_status():
    return _indexing_status
