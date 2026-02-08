"""SQLite-backed metadata store for code chunks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from hermes.chunking.base import Chunk
from hermes.logging import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id   INTEGER PRIMARY KEY,
    file_path  TEXT    NOT NULL,
    language   TEXT    NOT NULL,
    start_line INTEGER NOT NULL,
    end_line   INTEGER NOT NULL,
    code_text  TEXT    NOT NULL,
    symbol_name TEXT   NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_chunks_lang ON chunks(language);
"""

class MetadataStore:
    """Stores and retrieves chunk metadata in a local SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
        return self._conn

    def insert_chunks(self, chunks: list[Chunk]) -> list[int]:
        """Insert chunks and return their auto-assigned chunk_ids (0-indexed)."""
        cur = self.conn.cursor()
        ids: list[int] = []
        for chunk in chunks:
            cur.execute(
                "INSERT INTO chunks (file_path, language, start_line, end_line, code_text, symbol_name) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (chunk.file_path, chunk.language, chunk.start_line, chunk.end_line,
                chunk.code_text, chunk.symbol_name),
            )
            ids.append(cur.lastrowid)
        self.conn.commit()
        return ids

    def get_chunk(self, chunk_id: int) -> dict | None:
        cur = self.conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_chunks_by_ids(self, chunk_ids: list[int]) -> list[dict]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        cur = self.conn.execute(
            f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", chunk_ids
        )
        rows = cur.fetchall()
        by_id = {r[0]: self._row_to_dict(r) for r in rows}
        return [by_id[cid] for cid in chunk_ids if cid in by_id]

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM chunks")
        return cur.fetchone()[0]

    def all_chunk_ids(self) -> list[int]:
        cur = self.conn.execute("SELECT chunk_id FROM chunks ORDER BY chunk_id")
        return [row[0] for row in cur.fetchall()]

    def all_texts(self) -> list[str]:
        """Return code_text for all chunks ordered by chunk_id."""
        cur = self.conn.execute("SELECT code_text FROM chunks ORDER BY chunk_id")
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "chunk_id": row[0],
            "file_path": row[1],
            "language": row[2],
            "start_line": row[3],
            "end_line": row[4],
            "code_text": row[5],
            "symbol_name": row[6],
        }
