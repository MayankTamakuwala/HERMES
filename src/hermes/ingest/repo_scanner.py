"""Walk a repository and yield candidate source files for indexing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from hermes.ingest.language_detect import detect_language
from hermes.logging import get_logger

log = get_logger(__name__)

# Directories that should always be skipped
SKIP_DIRS: set[str] = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".tox", ".nox",
    "venv", ".venv", "env", ".env",
    ".idea", ".vscode",
    "dist", "build", ".eggs", "*.egg-info",
    "vendor", "third_party",
    "artifacts", "reports",
}

# Max file size to index (1 MB) - prevents binary blobs or generated files
MAX_FILE_BYTES: int = 1_048_576


@dataclass(frozen=True)
class ScannedFile:
    """A source file discovered in the repository."""

    path: Path
    relative_path: str
    language: str
    size_bytes: int


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def scan_repository(repo_root: Path, include_languages: set[str] | None = None) -> list[ScannedFile]:
    """Recursively scan *repo_root* and return indexable source files.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.
    include_languages:
        If provided, only include files whose detected language is in this set.
        When ``None``, all recognised languages are included.
    """
    repo_root = repo_root.resolve()
    results: list[ScannedFile] = []

    for dirpath, dirnames, filenames in os.walk(repo_root, topdown=True):
        # Prune directories in-place so os.walk skips them
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            lang = detect_language(fpath)
            if lang is None:
                continue
            if include_languages and lang not in include_languages:
                continue

            try:
                size = fpath.stat().st_size
            except OSError:
                continue

            if size == 0 or size > MAX_FILE_BYTES:
                continue

            rel = str(fpath.relative_to(repo_root))
            results.append(ScannedFile(path=fpath, relative_path=rel, language=lang, size_bytes=size))

    log.info("repo_scan_complete", repo=str(repo_root), files_found=len(results))
    return results
