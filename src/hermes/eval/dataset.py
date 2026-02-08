"""Auto-generate evaluation query -> chunk pairs from indexed code.

Strategy: for each chunk with a meaningful symbol name or docstring,
generate a natural-language query and treat that chunk as the relevant result.
"""

from __future__ import annotations

import ast
import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from hermes.index.metadata_store import MetadataStore
from hermes.logging import get_logger

log = get_logger(__name__)


@dataclass
class EvalPair:
    query: str
    relevant_chunk_id: int
    file_path: str
    symbol_name: str


def generate_eval_dataset(
    store: MetadataStore,
    max_queries: int = 200,
    seed: int = 42,
) -> list[EvalPair]:
    """Generate evaluation pairs from chunk metadata.

    Uses heuristics:
    1. Chunks with a symbol_name -> query: "What does <symbol_name> do?"
    2. Python chunks with docstrings -> use the docstring as the query
    3. Chunks with comments -> use the first comment as a query
    """
    rng = random.Random(seed)
    pairs: list[EvalPair] = []

    all_ids = store.all_chunk_ids()
    rng.shuffle(all_ids)

    for cid in all_ids:
        if len(pairs) >= max_queries:
            break

        meta = store.get_chunk(cid)
        if meta is None:
            continue

        query = _extract_query(meta)
        if query and len(query) >= 10:
            pairs.append(
                EvalPair(
                    query=query,
                    relevant_chunk_id=cid,
                    file_path=meta["file_path"],
                    symbol_name=meta.get("symbol_name", ""),
                )
            )

    log.info("eval_dataset_generated", n_pairs=len(pairs))
    return pairs


def _extract_query(meta: dict) -> str | None:
    """Try to extract a natural-language query from a chunk."""
    code = meta["code_text"]
    symbol = meta.get("symbol_name", "")

    # 1. Try to extract a docstring (Python)
    if meta["language"] == "python":
        doc = _extract_python_docstring(code)
        if doc:
            return doc

    # 2. Try leading comment
    comment = _extract_leading_comment(code)
    if comment and len(comment) > 15:
        return comment

    # 3. Fall back to symbol name
    if symbol and symbol not in ("<module>", "") and "::" not in symbol:
        readable = _symbol_to_query(symbol)
        return readable

    return None

def _extract_python_docstring(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ds = ast.get_docstring(node)
            if ds:
                first_line = ds.strip().split("\n")[0].strip()
                if len(first_line) >= 10:
                    return first_line
    return None


def _extract_leading_comment(code: str) -> str | None:
    lines = code.strip().splitlines()
    comments: list[str] = []
    for line in lines[:5]:
        stripped = line.strip()
        if stripped.startswith("#"):
            comments.append(stripped.lstrip("#").strip())
        elif stripped.startswith("//"):
            comments.append(stripped.lstrip("/").strip())
        elif stripped:
            break
    if comments:
        return " ".join(comments)
    return None


def _symbol_to_query(symbol: str) -> str:
    """Convert a symbol name like 'calculate_bmi' to 'How does calculate bmi work?'"""
    # Split camelCase and snake_case
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", symbol)
    words = words.replace("_", " ").lower()
    return f"How does {words} work?"


def save_eval_dataset(pairs: list[EvalPair], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(p) for p in pairs]
    path.write_text(json.dumps(data, indent=2))
    log.info("eval_dataset_saved", path=str(path), n=len(data))


def load_eval_dataset(path: Path) -> list[EvalPair]:
    data = json.loads(path.read_text())
    return [EvalPair(**d) for d in data]
