"""AST-based chunker for Python source files."""

from __future__ import annotations

import ast
from typing import ClassVar

from hermes.chunking.base import BaseChunker, Chunk, ChunkerRegistry
from hermes.logging import get_logger

log = get_logger(__name__)


@ChunkerRegistry.register
class PythonChunker(BaseChunker):
    supported_languages: ClassVar[list[str]] = ["python"]

    def chunk_file(self, source: str, file_path: str, language: str) -> list[Chunk]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            log.debug("ast_parse_failed_fallback", file=file_path)
            return self._fallback_chunk(source, file_path, language)

        lines = source.splitlines(keepends=True)
        chunks: list[Chunk] = []

        # Collect top-level definitions
        nodes: list[ast.AST] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes.append(node)

        if not nodes:
            # No top-level defs - fall back to line-based chunking
            return self._fallback_chunk(source, file_path, language)

        # Module-level preamble (imports, constants before first def)
        first_def_line = nodes[0].lineno
        if first_def_line > 1:
            preamble = "".join(lines[: first_def_line - 1])
            if len(preamble.strip()) >= self.config.min_chars:
                chunks.append(
                    Chunk(
                        file_path=file_path,
                        language=language,
                        start_line=1,
                        end_line=first_def_line - 1,
                        code_text=preamble,
                        symbol_name="<module>",
                    )
                )

        for node in nodes:
            start = node.lineno
            end = node.end_lineno or start
            text = "".join(lines[start - 1 : end])

            # If the block exceeds max_chars, split it into sub-chunks
            if len(text) > self.config.max_chars:
                sub_chunks = self._split_large_block(
                    text, file_path, language, start, getattr(node, "name", "")
                )
                chunks.extend(sub_chunks)
            else:
                name = getattr(node, "name", "")
                if len(text.strip()) >= self.config.min_chars:
                    chunks.append(
                        Chunk(
                            file_path=file_path,
                            language=language,
                            start_line=start,
                            end_line=end,
                            code_text=text,
                            symbol_name=name,
                        )
                    )

        return chunks

    def _split_large_block(
        self, text: str, file_path: str, language: str, global_start: int, symbol: str
    ) -> list[Chunk]:
        """Split an oversized block into line-based sub-chunks with overlap."""
        lines = text.splitlines(keepends=True)
        chunks: list[Chunk] = []
        max_lines = max(10, self.config.max_chars // 80)
        overlap = self.config.overlap_lines
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

    def _fallback_chunk(self, source: str, file_path: str, language: str) -> list[Chunk]:
        from hermes.chunking.heuristic_chunker import HeuristicChunker

        return HeuristicChunker(self.config).chunk_file(source, file_path, language)
