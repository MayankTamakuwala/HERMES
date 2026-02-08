"""Cross-encoder wrapper for reranking (query, code) pairs."""

from __future__ import annotations

import numpy as np
from sentence_transformers import CrossEncoder as _CrossEncoder

from hermes.config import EmbedConfig
from hermes.logging import get_logger

log = get_logger(__name__)


class CrossEncoder:
    """Wraps a cross-encoder model for scoring (query, passage) pairs."""

    def __init__(self, config: EmbedConfig) -> None:
        self.config = config
        log.info("loading_crossencoder", model=config.crossencoder_model)
        self.model = _CrossEncoder(
            config.crossencoder_model,
            max_length=config.crossencoder_max_length,
        )

    def score_pairs(self, query: str, passages: list[str]) -> np.ndarray:
        """Return relevance scores for each (query, passage) pair.

        Returns a 1-D float32 array of length ``len(passages)``.
        """
        if not passages:
            return np.array([], dtype=np.float32)

        pairs = [[query, p] for p in passages]
        scores = self.model.predict(
            pairs,
            batch_size=self.config.crossencoder_batch_size,
            show_progress_bar=False,
        )
        return np.asarray(scores, dtype=np.float32)
