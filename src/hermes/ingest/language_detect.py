"""Map file extensions to programming languages."""

from __future__ import annotations

from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".lua": "lua",
    ".sql": "sql",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}

# Languages we attempt AST / structural chunking for
STRUCTURAL_LANGUAGES = {"python", "javascript", "typescript", "java", "go"}

# Languages we consider "code" (vs config/docs)
CODE_LANGUAGES = {
    "python", "javascript", "typescript", "java", "go", "rust",
    "c", "cpp", "csharp", "ruby", "php", "swift", "kotlin", "scala",
    "lua", "shell", "r",
}


def detect_language(path: Path) -> str | None:
    """Return the language string for a file path, or None if unknown."""
    return EXTENSION_MAP.get(path.suffix.lower())


def is_code_file(path: Path) -> bool:
    """Return True if the file is a recognised code file."""
    lang = detect_language(path)
    return lang is not None and lang in CODE_LANGUAGES
