"""Bi-encoder wrapper for dense embedding of code chunks and queries."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from hermes.config import EmbedConfig
from hermes.logging import get_logger

log = get_logger(__name__)


class BiEncoder:
    """Wraps a sentence-transformers model for encoding chunks and queries."""

    def __init__(self, config: EmbedConfig) -> None:
        self.config = config
        log.info("loading_biencoder", model=config.biencoder_model)
        self.model = SentenceTransformer(config.biencoder_model)
        self.model.max_seq_length = config.biencoder_max_length
        self._dim: int | None = None

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = self.model.get_sentence_embedding_dimension()
        return self._dim

    def encode_texts(self, texts: list[str], show_progress: bool = True) -> np.ndarray:
        """Encode a batch of texts, returning a float32 numpy array (N, dim)."""
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.biencoder_batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string, returning shape (1, dim)."""
        vec = self.model.encode(
            [query],
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vec.astype(np.float32)
