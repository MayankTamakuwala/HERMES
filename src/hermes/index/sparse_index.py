"""BM25 sparse index for hybrid retrieval."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from hermes.logging import get_logger

log = get_logger(__name__)

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + camelCase/snake_case tokenizer for code."""
    # Split on non-alphanumeric, then split camelCase
    tokens = re.findall(r"[a-zA-Z]+|[0-9]+", text)
    expanded: list[str] = []
    for tok in tokens:
        # Split camelCase
        parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", tok).split()
        expanded.extend(p.lower() for p in parts if len(p) > 1)
    return expanded

class SparseIndex:
    """BM25-based sparse retrieval over code chunks."""

    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._corpus_tokens: list[list[str]] = []

    def build(self, texts: list[str]) -> None:
        self._corpus_tokens = [_tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(self._corpus_tokens)
        log.info("sparse_index_built", n_docs=len(texts))

    def search(self, query: str, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (scores, ids) arrays of length top_k."""
        assert self._bm25 is not None, "Sparse index not built"
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        top_scores = scores[top_indices]
        return top_scores.astype(np.float32), top_indices.astype(np.int64)

    def save(self, path: Path) -> None:
        data = {"corpus_tokens": self._corpus_tokens}
        path.write_text(json.dumps(data))
        log.info("sparse_index_saved", path=str(path))

    def load(self, path: Path) -> None:
        data = json.loads(path.read_text())
        self._corpus_tokens = data["corpus_tokens"]
        self._bm25 = BM25Okapi(self._corpus_tokens)
        log.info("sparse_index_loaded", n_docs=len(self._corpus_tokens))
