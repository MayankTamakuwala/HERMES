"""Generic line-based chunker with overlap, used as a fallback for any language."""

from __future__ import annotations

import re
from typing import ClassVar

from hermes.chunking.base import BaseChunker, Chunk

# Patterns that hint at block boundaries (language-agnostic)
_BLOCK_HINT = re.compile(
    r"^(?:func |fn |def |class |public |private |protected |interface |struct |impl |module )",
    re.MULTILINE,
)


class HeuristicChunker(BaseChunker):
    """Splits source into fixed-size chunks with overlap, trying to break at
    structural boundaries when possible."""

    supported_languages: ClassVar[list[str]] = []  # catch-all, not registered

    def chunk_file(self, source: str, file_path: str, language: str) -> list[Chunk]:
        lines = source.splitlines(keepends=True)
        if not lines:
            return []

        max_lines = max(10, self.config.max_chars // 80)
        overlap = self.config.overlap_lines
        chunks: list[Chunk] = []

        i = 0
        while i < len(lines):
            # Try to find a natural break point near the end of the window
            window_end = min(i + max_lines, len(lines))
            break_at = window_end

            # Look backwards from window_end for a block-start line
            for j in range(window_end - 1, max(i + max_lines // 2, i), -1):
                if j < len(lines) and _BLOCK_HINT.match(lines[j]):
                    break_at = j
                    break

            text = "".join(lines[i:break_at])
            if len(text.strip()) >= self.config.min_chars:
                chunks.append(
                    Chunk(
                        file_path=file_path,
                        language=language,
                        start_line=i + 1,
                        end_line=break_at,
                        code_text=text,
                    )
                )

            # Advance with overlap
            if break_at >= len(lines):
                break
            i = break_at - overlap if break_at - overlap > i else break_at

        return chunks
