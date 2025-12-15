from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
import discord

import logging.config
from src.matthews_order_backend.logger.logging_config import LOGGING_CONFIG
from src.matthews_order_backend.logger.logger import get_logger

from src.matthews_order_backend.models import ConfigRepository
from src.matthews_order_backend.app_utils import get_settings
from src.matthews_order_backend.endpoints.rest.order_endpoint import router as order_router
from src.matthews_order_backend.endpoints.discord.order_event import OrderDiscordClient


logging.config.dictConfig(LOGGING_CONFIG)
logger = get_logger("matthews_order_backend.app")


_config_repo: ConfigRepository | None = None

def _get_config_repo() -> ConfigRepository:
    global _config_repo
    settings = get_settings()
    if _config_repo is None or _config_repo.source_path != settings.api_config_path:
        _config_repo = ConfigRepository(settings.api_config_path)
    return _config_repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Matthews Back Order API ready (log level: %s)", get_settings().log_level)
    yield


# Init FastAPI app
app = FastAPI(
    title="Matthews-Back Order API",
    description="Generic action execution API driven by api_config.json definitions.",
    version="0.1.0",
    lifespan=lifespan,
)
# Init Discord client
intents = discord.Intents.default()
intents.message_content = True
app_discord = OrderDiscordClient(intents=intents)

logger.info("Starting Matthews Back Order API...")


# Health endpoint
@app.get("/healthz", summary="Health probe")
async def healthz() -> dict[str, str]:
    """Simple health endpoint used by orchestration platforms."""
    return {"status": "ok"}


# Include routers for FastAPI app
# app.include_router(order_router, prefix="/order")
# Include events for Discord client
app_discord.run(get_settings().discord_bot_token)


def main():
    import uvicorn
    uvicorn.run(
        "src.matthews_order_backend.app:app",
        host="0.0.0.0",
        port=8000,
        # reload=True
    )


if __name__ == "__main__":

    main()
