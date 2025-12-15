from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

import logging.config
from src.matthews_order_backend.logger.logging_config import LOGGING_CONFIG
from src.matthews_order_backend.logger.logger import get_logger

from src.matthews_order_backend.models import ConfigRepository
from src.matthews_order_backend.app_utils import get_settings
from src.matthews_order_backend.endpoints.rest.order_endpoint import router as order_router
from src.matthews_order_backend.endpoints.rest.base_endpoint import router as base_router
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


def main_api():
    import uvicorn
    # Include routers for FastAPI app
    app.include_router(base_router, prefix="")
    app.include_router(order_router, prefix="/order")
    # Run FastAPI app with Uvicorn
    uvicorn.run(
        "src.matthews_order_backend.app:app",
        host="0.0.0.0",
        port=8000,
        # reload=True
    )


def main_discord():
    import discord
    # Init Discord client
    intents = discord.Intents.default()
    intents.message_content = True
    app_discord = OrderDiscordClient(intents=intents)
    # Include events for Discord client
    logger.info("Starting Matthews Back Order Discord Bot")
    app_discord.run(get_settings().discord_bot_token)


if __name__ == "__main__":
    import sys

    param1 = sys.argv[1] if len(sys.argv) > 1 else "api"

    match param1:

        case "api":

            main_api()

        case "discord":

            main_discord()

        case _:

            logger.error("Invalid parameter. Use 'api' or 'discord'.")
