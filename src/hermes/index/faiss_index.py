"""FAISS index wrapper for dense vector search."""

from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np

from hermes.config import IndexConfig
from hermes.logging import get_logger

log = get_logger(__name__)

class FaissIndex:
    """Build, save, load, and query a FAISS index."""

    def __init__(self, config: IndexConfig, dim: int) -> None:
        self.config = config
        self.dim = dim
        self._index: faiss.Index | None = None

    def build(self, embeddings: np.ndarray) -> None:
        """Build the index from an (N, dim) float32 matrix."""
        n = embeddings.shape[0]
        log.info("building_faiss_index", n_vectors=n, dim=self.dim,
                use_ivf=self.config.faiss_use_ivf)

        if self.config.faiss_use_ivf and n > self.config.faiss_ivf_nlist * 40:
            quantizer = faiss.IndexFlatIP(self.dim)
            self._index = faiss.IndexIVFFlat(
                quantizer, self.dim, self.config.faiss_ivf_nlist, faiss.METRIC_INNER_PRODUCT
            )
            self._index.train(embeddings)
            self._index.add(embeddings)
            self._index.nprobe = self.config.faiss_nprobe
        else:
            # Flat index - exact search, fine for <100k vectors
            self._index = faiss.IndexFlatIP(self.dim)
            self._index.add(embeddings)

        log.info("faiss_index_built", total=self._index.ntotal)

    def search(self, query_vec: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        """Search the index. Returns (scores, ids) each of shape (1, top_k)."""
        assert self._index is not None, "Index not built or loaded"
        top_k = min(top_k, self._index.ntotal)
        scores, ids = self._index.search(query_vec, top_k)
        return scores, ids

    def save(self, path: Path) -> None:
        assert self._index is not None
        faiss.write_index(self._index, str(path))
        log.info("faiss_index_saved", path=str(path))

    def load(self, path: Path) -> None:
        self._index = faiss.read_index(str(path))
        self.dim = self._index.d
        if hasattr(self._index, "nprobe"):
            self._index.nprobe = self.config.faiss_nprobe
        log.info("faiss_index_loaded", path=str(path), total=self._index.ntotal)

    @property
    def ntotal(self) -> int:
        return self._index.ntotal if self._index else 0
