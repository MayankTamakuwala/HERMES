"""API route definitions for the HERMES query service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from hermes.search.schemas import SearchRequest, SearchResponse, StatsResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/")
async def index():
    return await health()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request):
    pipeline = request.app.state.pipeline
    return pipeline.search(req)


@router.get("/stats", response_model=StatsResponse)
async def stats(request: Request):
    pipeline = request.app.state.pipeline
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
    pipeline = request.app.state.pipeline
    pipeline.reload()
    return {"status": "reloaded", "n_chunks": pipeline.store.count()}
