"""LRU caching for query embeddings and reranking scores."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from threading import Lock

import numpy as np


class EmbeddingCache:
    """Thread-safe LRU cache for query embeddings."""

    def __init__(self, max_size: int = 1024) -> None:
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def _key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> np.ndarray | None:
        k = self._key(text)
        with self._lock:
            if k in self._cache:
                self._cache.move_to_end(k)
                self.hits += 1
                return self._cache[k]
            self.misses += 1
            return None

    def put(self, text: str, embedding: np.ndarray) -> None:
        k = self._key(text)
        with self._lock:
            if k in self._cache:
                self._cache.move_to_end(k)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
                self._cache[k] = embedding

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
