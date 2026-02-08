"""Pydantic models for search requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    top_k_retrieve: int = Field(100, ge=1, le=1000)
    top_k_rerank: int = Field(10, ge=1, le=200)
    retrieval_mode: str | None = Field(None, pattern=r"^(dense|sparse|hybrid)$")
    filter_language: str | None = None
    filter_path_prefix: str | None = None
    return_snippets: bool = True


class SearchResultItem(BaseModel):
    chunk_id: int
    file_path: str
    language: str
    start_line: int
    end_line: int
    symbol_name: str = ""
    code_snippet: str | None = None
    retrieval_rank: int
    retrieval_score: float
    rerank_score: float | None = None
    final_rank: int


class SearchResponse(BaseModel):
    request_id: str
    query: str
    retrieval_mode: str
    results: list[SearchResultItem]
    timings_ms: dict[str, float]
    rerank_skipped: bool = False
    total_candidates: int = 0


class StatsResponse(BaseModel):
    index_size: int
    n_chunks: int
    biencoder_model: str
    crossencoder_model: str
    retrieval_mode: str
    cache_hit_rate: float
    cache_hits: int
    cache_misses: int
