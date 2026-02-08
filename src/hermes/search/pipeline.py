"""Core search pipeline: retrieve -> (fuse) -> rerank -> return."""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

import numpy as np

from hermes.config import HermesConfig
from hermes.embed.biencoder import BiEncoder
from hermes.embed.cache import EmbeddingCache
from hermes.embed.crossencoder import CrossEncoder
from hermes.index.faiss_index import FaissIndex
from hermes.index.metadata_store import MetadataStore
from hermes.index.sparse_index import SparseIndex
from hermes.logging import get_logger
from hermes.search.fusion import reciprocal_rank_fusion
from hermes.search.schemas import SearchRequest, SearchResponse, SearchResultItem

log = get_logger(__name__)

class SearchPipeline:
    """Loads artifacts and executes the multi-stage search pipeline."""

    def __init__(self, config: HermesConfig) -> None:
        self.config = config
        artifacts = config.artifacts_dir

        self.store = MetadataStore(artifacts / "metadata.db")

        self.biencoder = BiEncoder(config.embed)
        self.faiss_index = FaissIndex(config.index, dim=self.biencoder.dim)
        self.faiss_index.load(artifacts / "faiss.index")

        self.crossencoder = CrossEncoder(config.embed)

        # Load sparse index if needed
        self._sparse: SparseIndex | None = None
        sparse_path = artifacts / "sparse_index.json"
        if sparse_path.exists():
            self._sparse = SparseIndex()
            self._sparse.load(sparse_path)

        self._cache = EmbeddingCache(max_size=config.embed.query_cache_size)
        self._pool = ThreadPoolExecutor(max_workers=2)
        self._chunk_ids = self.store.all_chunk_ids()

        log.info("search_pipeline_ready", n_chunks=len(self._chunk_ids))

    # Public Functions

    def search(self, request: SearchRequest) -> SearchResponse:
        request_id = uuid.uuid4().hex[:12]
        timings: dict[str, float] = {}
        mode = request.retrieval_mode or self.config.search.retrieval_mode

        # 1. Embed query
        t0 = time.perf_counter()
        query_vec = self._embed_query(request.query)
        timings["embed_query_ms"] = _ms(t0)

        # 2. Retrieval
        t1 = time.perf_counter()
        candidates = self._retrieve(request.query, query_vec, request.top_k_retrieve, mode)
        timings["retrieval_ms"] = _ms(t1)

        # 3. Apply filters
        if request.filter_language or request.filter_path_prefix:
            candidates = self._apply_filters(
                candidates, request.filter_language, request.filter_path_prefix
            )

        total_candidates = len(candidates)

        # 4. Rerank
        rerank_skipped = False
        t2 = time.perf_counter()
        max_rerank = self.config.search.max_rerank_candidates
        rerank_candidates = candidates[:max_rerank]

        if rerank_candidates:
            try:
                reranked = self._rerank_with_timeout(request.query, rerank_candidates)
                candidates = reranked + candidates[max_rerank:]
            except FuturesTimeout:
                log.warning("rerank_timeout", request_id=request_id)
                rerank_skipped = True

        timings["rerank_ms"] = _ms(t2)

        # 5. Build results
        final = candidates[: request.top_k_rerank]
        results = self._build_results(final, request.return_snippets)

        timings["total_ms"] = _ms(t0)

        return SearchResponse(
            request_id=request_id,
            query=request.query,
            retrieval_mode=mode,
            results=results,
            timings_ms={k: round(v, 2) for k, v in timings.items()},
            rerank_skipped=rerank_skipped,
            total_candidates=total_candidates,
        )

    @property
    def embedding_cache(self) -> EmbeddingCache:
        return self._cache

    def reload(self, config: HermesConfig | None = None) -> None:
        """Reload artifacts from disk."""
        if config:
            self.config = config
        artifacts = self.config.artifacts_dir
        self.store.close()
        self.store = MetadataStore(artifacts / "metadata.db")
        self.faiss_index.load(artifacts / "faiss.index")
        self._chunk_ids = self.store.all_chunk_ids()
        if self._sparse and (artifacts / "sparse_index.json").exists():
            self._sparse.load(artifacts / "sparse_index.json")
        self._cache.clear()
        log.info("pipeline_reloaded")

    # Private Functions

    def _embed_query(self, query: str) -> np.ndarray:
        cached = self._cache.get(query)
        if cached is not None:
            return cached
        vec = self.biencoder.encode_query(query)
        self._cache.put(query, vec)
        return vec

    def _retrieve(
        self, query: str, query_vec: np.ndarray, top_k: int, mode: str
    ) -> list[_Candidate]:
        if mode == "dense":
            return self._dense_retrieve(query_vec, top_k)
        elif mode == "sparse":
            return self._sparse_retrieve(query, top_k)
        else:  # hybrid
            dense = self._dense_retrieve(query_vec, top_k)
            sparse = self._sparse_retrieve(query, top_k)
            return self._fuse(dense, sparse, top_k)

    def _dense_retrieve(self, query_vec: np.ndarray, top_k: int) -> list[_Candidate]:
        scores, ids = self.faiss_index.search(query_vec, top_k)
        candidates = []
        for rank, (score, idx) in enumerate(zip(scores[0], ids[0])):
            if idx < 0 or idx >= len(self._chunk_ids):
                continue
            db_id = self._chunk_ids[idx]
            candidates.append(_Candidate(chunk_id=db_id, retrieval_score=float(score), retrieval_rank=rank + 1))
        return candidates

    def _sparse_retrieve(self, query: str, top_k: int) -> list[_Candidate]:
        if self._sparse is None:
            return []
        scores, ids = self._sparse.search(query, top_k)
        candidates = []
        for rank, (score, idx) in enumerate(zip(scores, ids)):
            idx_int = int(idx)
            if idx_int < 0 or idx_int >= len(self._chunk_ids):
                continue
            db_id = self._chunk_ids[idx_int]
            candidates.append(_Candidate(chunk_id=db_id, retrieval_score=float(score), retrieval_rank=rank + 1))
        return candidates

    def _fuse(self, dense: list[_Candidate], sparse: list[_Candidate], top_k: int) -> list[_Candidate]:
        dense_pairs = [(c.chunk_id, c.retrieval_score) for c in dense]
        sparse_pairs = [(c.chunk_id, c.retrieval_score) for c in sparse]
        fused = reciprocal_rank_fusion([dense_pairs, sparse_pairs], k=self.config.search.rrf_k, top_n=top_k)
        return [
            _Candidate(chunk_id=cid, retrieval_score=score, retrieval_rank=rank + 1)
            for rank, (cid, score) in enumerate(fused)
        ]

    def _rerank_with_timeout(self, query: str, candidates: list[_Candidate]) -> list[_Candidate]:
        future = self._pool.submit(self._rerank, query, candidates)
        timeout = self.config.search.rerank_timeout_seconds
        return future.result(timeout=timeout)

    def _rerank(self, query: str, candidates: list[_Candidate]) -> list[_Candidate]:
        chunk_ids = [c.chunk_id for c in candidates]
        metas = self.store.get_chunks_by_ids(chunk_ids)
        texts = [m["code_text"] for m in metas]

        scores = self.crossencoder.score_pairs(query, texts)

        for cand, score in zip(candidates, scores):
            cand.rerank_score = float(score)

        candidates.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return candidates

    def _apply_filters(
        self, candidates: list[_Candidate], language: str | None, path_prefix: str | None
    ) -> list[_Candidate]:
        chunk_ids = [c.chunk_id for c in candidates]
        metas = self.store.get_chunks_by_ids(chunk_ids)
        meta_map = {m["chunk_id"]: m for m in metas}

        filtered = []
        for c in candidates:
            m = meta_map.get(c.chunk_id)
            if m is None:
                continue
            if language and m["language"] != language:
                continue
            if path_prefix and not m["file_path"].startswith(path_prefix):
                continue
            filtered.append(c)
        return filtered

    def _build_results(self, candidates: list[_Candidate], return_snippets: bool) -> list[SearchResultItem]:
        chunk_ids = [c.chunk_id for c in candidates]
        metas = self.store.get_chunks_by_ids(chunk_ids)
        meta_map = {m["chunk_id"]: m for m in metas}

        results = []
        for final_rank, c in enumerate(candidates, 1):
            m = meta_map.get(c.chunk_id)
            if m is None:
                continue
            results.append(
                SearchResultItem(
                    chunk_id=c.chunk_id,
                    file_path=m["file_path"],
                    language=m["language"],
                    start_line=m["start_line"],
                    end_line=m["end_line"],
                    symbol_name=m.get("symbol_name", ""),
                    code_snippet=m["code_text"] if return_snippets else None,
                    retrieval_rank=c.retrieval_rank,
                    retrieval_score=round(c.retrieval_score, 4),
                    rerank_score=round(c.rerank_score, 4) if c.rerank_score is not None else None,
                    final_rank=final_rank,
                )
            )
        return results


class _Candidate:
    """Internal mutable candidate during pipeline execution."""

    __slots__ = ("chunk_id", "retrieval_score", "retrieval_rank", "rerank_score")

    def __init__(self, chunk_id: int, retrieval_score: float, retrieval_rank: int) -> None:
        self.chunk_id = chunk_id
        self.retrieval_score = retrieval_score
        self.retrieval_rank = retrieval_rank
        self.rerank_score: float | None = None

def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
