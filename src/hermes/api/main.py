"""FastAPI application factory for the HERMES query service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from hermes.api.routes import router
from hermes.config import HermesConfig, load_config
from hermes.logging import setup_logging
from hermes.search.pipeline import SearchPipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the search pipeline on startup."""
    config: HermesConfig = app.state.config
    setup_logging(level=config.log_level, json_output=config.log_json)
    app.state.pipeline = SearchPipeline(config)
    yield
    app.state.pipeline.store.close()


def create_app(config: HermesConfig | None = None) -> FastAPI:
    """Build and return the FastAPI application."""
    if config is None:
        config = load_config()

    app = FastAPI(
        title="HERMES",
        description="Hybrid Embedding Retrieval with Multi-stage Evaluation & Scoring",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.config = config
    app.include_router(router)
    return app
