"""Orchestrates the full offline indexing pipeline."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from hermes.chunking import get_chunker
from hermes.chunking.base import Chunk
from hermes.config import HermesConfig
from hermes.embed.biencoder import BiEncoder
from hermes.index.faiss_index import FaissIndex
from hermes.index.metadata_store import MetadataStore
from hermes.index.sparse_index import SparseIndex
from hermes.ingest.repo_scanner import ScannedFile, scan_repository
from hermes.logging import get_logger

log = get_logger(__name__)

def build_index(repo_path: Path, config: HermesConfig) -> dict:
    """Run the full indexing pipeline: scan -> chunk -> embed -> build index.

    Returns a summary dict with timing and count information.
    """
    artifacts = config.artifacts_dir
    artifacts.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    # 1. Scan repository
    log.info("phase_scan", repo=str(repo_path))
    files = scan_repository(repo_path)
    if not files:
        raise ValueError(f"No indexable files found in {repo_path}")

    # 2. Chunk files
    log.info("phase_chunk", n_files=len(files))
    all_chunks: list[Chunk] = []
    for sf in files:
        try:
            source = sf.path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            log.warning("read_failed", file=sf.relative_path, error=str(exc))
            continue
        chunker = get_chunker(sf.language, config.chunking)
        chunks = chunker.chunk_file(source, sf.relative_path, sf.language)
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError("Chunking produced zero chunks")

    log.info("chunking_complete", n_chunks=len(all_chunks))
    t_chunk = time.perf_counter()

    # 3. Store metadata
    db_path = artifacts / "metadata.db"
    store = MetadataStore(db_path)
    chunk_ids = store.insert_chunks(all_chunks)
    log.info("metadata_stored", n_chunks=len(chunk_ids))

    # 4. Embed chunks
    log.info("phase_embed")
    biencoder = BiEncoder(config.embed)
    texts = [c.code_text for c in all_chunks]
    embeddings = biencoder.encode_texts(texts)
    t_embed = time.perf_counter()

    # 5. Build FAISS index
    log.info("phase_faiss_build")
    faiss_idx = FaissIndex(config.index, dim=biencoder.dim)
    faiss_idx.build(embeddings)
    faiss_idx.save(artifacts / "faiss.index")

    # 6. Save raw embeddings for potential re-use
    np.save(str(artifacts / "embeddings.npy"), embeddings)

    # 7. Build sparse index (for hybrid mode)
    sparse = SparseIndex()
    sparse.build(texts)
    sparse.save(artifacts / "sparse_index.json")

    t_end = time.perf_counter()
    store.close()

    summary = {
        "n_files": len(files),
        "n_chunks": len(all_chunks),
        "embedding_dim": biencoder.dim,
        "biencoder_model": config.embed.biencoder_model,
        "time_chunk_s": round(t_chunk - t0, 2),
        "time_embed_s": round(t_embed - t_chunk, 2),
        "time_total_s": round(t_end - t0, 2),
        "chunks_per_sec": round(len(all_chunks) / (t_end - t0), 1),
    }
    log.info("indexing_complete", **summary)
    return summary
