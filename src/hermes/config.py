"""Central configuration for HERMES, driven by env vars and/or config file."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class ChunkingConfig(BaseSettings):
    """Controls how source files are split into searchable chunks."""

    model_config = {"env_prefix": "HERMES_CHUNK_", "env_file": ".env", "extra": "ignore"}

    max_chars: int = Field(1500, description="Maximum characters per chunk")
    overlap_lines: int = Field(3, description="Lines of overlap between consecutive chunks")
    min_chars: int = Field(50, description="Discard chunks shorter than this")


class EmbedConfig(BaseSettings):
    """Bi-encoder and cross-encoder model settings."""

    model_config = {"env_prefix": "HERMES_EMBED_", "env_file": ".env", "extra": "ignore"}

    # Bi-encoder: all-MiniLM-L6-v2 is 80 MB, fast on CPU, and decent at
    # code/NL similarity. For better code-specific results swap to
    # "flax-sentence-embeddings/st-codesearch-distilroberta-base" or
    # "BAAI/bge-small-en-v1.5".
    biencoder_model: str = Field(
        "all-MiniLM-L6-v2",
        description="Sentence-transformers model id for bi-encoder",
    )
    biencoder_batch_size: int = 64
    biencoder_max_length: int = 512

    # Cross-encoder: cross-encoder/ms-marco-MiniLM-L-6-v2 is ~80 MB and
    # provides a reasonable quality/latency tradeoff for reranking on CPU.
    crossencoder_model: str = Field(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model id for reranking",
    )
    crossencoder_batch_size: int = 16
    crossencoder_max_length: int = 512

    query_cache_size: int = Field(1024, description="LRU cache size for query embeddings")


class IndexConfig(BaseSettings):
    """FAISS index and sparse index settings."""

    model_config = {"env_prefix": "HERMES_INDEX_", "env_file": ".env", "extra": "ignore"}

    faiss_nprobe: int = Field(8, description="Number of probes for IVF index (if used)")
    faiss_use_ivf: bool = Field(
        False,
        description="Use IVF index for large repos (>100k chunks). Flat is used otherwise.",
    )
    faiss_ivf_nlist: int = Field(100, description="Number of IVF clusters")


class SearchConfig(BaseSettings):
    """Search pipeline defaults."""

    model_config = {"env_prefix": "HERMES_SEARCH_", "env_file": ".env", "extra": "ignore"}

    top_k_retrieve: int = Field(100, description="Candidates from retrieval stage")
    top_k_rerank: int = Field(10, description="Final results after reranking")
    max_rerank_candidates: int = Field(50, description="Cap on candidates sent to cross-encoder")
    rerank_timeout_seconds: float = Field(
        10.0, description="If reranking exceeds this, return retrieval-only results"
    )
    retrieval_mode: Literal["dense", "sparse", "hybrid"] = Field(
        "dense", description="Retrieval strategy"
    )
    rrf_k: int = Field(60, description="RRF constant for reciprocal rank fusion")


class HermesConfig(BaseSettings):
    """Top-level HERMES configuration."""

    model_config = {"env_prefix": "HERMES_", "env_file": ".env", "extra": "ignore"}

    artifacts_dir: Path = Field(Path("artifacts"), description="Where index artifacts are stored")
    log_level: str = Field("INFO", description="Logging level")
    log_json: bool = Field(False, description="Emit JSON-formatted logs")

    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embed: EmbedConfig = Field(default_factory=EmbedConfig)
    index: IndexConfig = Field(default_factory=IndexConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)


def load_config(**overrides) -> HermesConfig:
    """Create a config instance, applying any programmatic overrides."""
    return HermesConfig(**overrides)
