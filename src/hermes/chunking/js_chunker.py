"""Heuristic structural chunker for JavaScript and TypeScript.

Uses regex-based detection of function/class boundaries since we don't
bundle a full JS/TS parser.  Falls back to the generic heuristic chunker
when no structural boundaries are found.
"""

from __future__ import annotations

import re
from typing import ClassVar

from hermes.chunking.base import BaseChunker, Chunk, ChunkerRegistry

# Patterns that indicate the start of a top-level block
_BLOCK_START = re.compile(
    r"^(?:export\s+)?(?:default\s+)?"
    r"(?:(?:async\s+)?function\s+\w+|class\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()",
    re.MULTILINE,
)


@ChunkerRegistry.register
class JSChunker(BaseChunker):
    supported_languages: ClassVar[list[str]] = ["javascript", "typescript"]

    def chunk_file(self, source: str, file_path: str, language: str) -> list[Chunk]:
        lines = source.splitlines(keepends=True)
        boundaries = self._find_boundaries(lines)

        if len(boundaries) < 2:
            from hermes.chunking.heuristic_chunker import HeuristicChunker
            return HeuristicChunker(self.config).chunk_file(source, file_path, language)

        chunks: list[Chunk] = []

        for idx, start_line in enumerate(boundaries):
            end_line = (boundaries[idx + 1] - 1) if idx + 1 < len(boundaries) else len(lines)
            text = "".join(lines[start_line:end_line])

            if len(text.strip()) < self.config.min_chars:
                continue

            # Extract symbol name from first line
            first = lines[start_line].strip()
            symbol = self._extract_symbol(first)

            if len(text) > self.config.max_chars:
                chunks.extend(self._split_large(text, file_path, language, start_line + 1, symbol))
            else:
                chunks.append(
                    Chunk(
                        file_path=file_path,
                        language=language,
                        start_line=start_line + 1,
                        end_line=end_line,
                        code_text=text,
                        symbol_name=symbol,
                    )
                )

        return chunks

    def _find_boundaries(self, lines: list[str]) -> list[int]:
        """Return 0-indexed line numbers where blocks start."""
        bounds = [0]
        for i, line in enumerate(lines):
            if i == 0:
                continue
            if _BLOCK_START.match(line):
                bounds.append(i)
        return bounds

    @staticmethod
    def _extract_symbol(line: str) -> str:
        m = re.search(r"(?:function|class|const|let|var)\s+(\w+)", line)
        return m.group(1) if m else ""

    def _split_large(
        self, text: str, file_path: str, language: str, global_start: int, symbol: str
    ) -> list[Chunk]:
        lines = text.splitlines(keepends=True)
        max_lines = max(10, self.config.max_chars // 80)
        overlap = self.config.overlap_lines
        chunks: list[Chunk] = []
        i = 0
        part = 0
        while i < len(lines):
            end_i = min(i + max_lines, len(lines))
            chunk_text = "".join(lines[i:end_i])
            if len(chunk_text.strip()) >= self.config.min_chars:
                chunks.append(
                    Chunk(
                        file_path=file_path,
                        language=language,
                        start_line=global_start + i,
                        end_line=global_start + end_i - 1,
                        code_text=chunk_text,
                        symbol_name=f"{symbol}::part{part}",
                    )
                )
            part += 1
            i = end_i - overlap if end_i < len(lines) else end_i
        return chunks
