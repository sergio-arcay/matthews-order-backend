from __future__ import annotations

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.matthews_order_backend.models import ConfigRepository
from src.matthews_order_backend.app_utils import get_settings
from src.matthews_order_backend.endpoints.v1.order_endpoint import router as order_router

logger = logging.getLogger(__name__)


_config_repo: ConfigRepository | None = None

def _get_config_repo() -> ConfigRepository:
    global _config_repo
    settings = get_settings()
    if _config_repo is None or _config_repo.source_path != settings.api_config_path:
        _config_repo = ConfigRepository(settings.api_config_path)
    return _config_repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    configured_level = get_settings().log_level.upper()
    log_level = getattr(logging, configured_level, logging.INFO)
    logging.basicConfig(level=log_level)
    logger.info("Matthews Back Order API ready (log level: %s)", configured_level)
    yield


app = FastAPI(
    title="Matthews-Back Order API",
    description="Generic action execution API driven by api_config.json definitions.",
    version="0.1.0",
    lifespan=lifespan,
)


# Health endpoint
@app.get("/healthz", summary="Health probe")
async def healthz() -> dict[str, str]:
    """Simple health endpoint used by orchestration platforms."""
    return {"status": "ok"}


# Include routers
app.include_router(order_router, prefix="/order")


def main():
    import uvicorn
    uvicorn.run("src.matthews_order_backend.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":

    main()
