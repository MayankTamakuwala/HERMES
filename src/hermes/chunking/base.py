"""Base types and registry for code chunkers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from hermes.config import ChunkingConfig


@dataclass(frozen=True)
class Chunk:
    """A contiguous block of source code extracted from a file."""

    file_path: str
    language: str
    start_line: int  # 1-indexed
    end_line: int    # inclusive
    code_text: str
    symbol_name: str = ""  # best-effort: function/class name


class BaseChunker(ABC):
    """Interface that all language-specific chunkers implement."""

    # Subclasses declare which languages they handle
    supported_languages: ClassVar[list[str]] = []

    def __init__(self, config: ChunkingConfig) -> None:
        self.config = config

    @abstractmethod
    def chunk_file(self, source: str, file_path: str, language: str) -> list[Chunk]:
        """Split *source* into chunks, returning them with metadata."""
        pass


class ChunkerRegistry:
    """Maintains a mapping from language -> chunker class."""

    _registry: ClassVar[dict[str, type[BaseChunker]]] = {}

    @classmethod
    def register(cls, chunker_cls: type[BaseChunker]) -> type[BaseChunker]:
        for lang in chunker_cls.supported_languages:
            cls._registry[lang] = chunker_cls
        return chunker_cls

    @classmethod
    def get(cls, language: str) -> type[BaseChunker] | None:
        return cls._registry.get(language)


def get_chunker(language: str, config: ChunkingConfig) -> BaseChunker:
    """Return an instantiated chunker for *language*, falling back to heuristic."""
    # Lazy imports to avoid circular deps, registry is populated on first call
    from hermes.chunking.heuristic_chunker import HeuristicChunker
    from hermes.chunking.js_chunker import JSChunker
    from hermes.chunking.python_chunker import PythonChunker

    cls = ChunkerRegistry.get(language)
    if cls is None:
        return HeuristicChunker(config)
    return cls(config)
