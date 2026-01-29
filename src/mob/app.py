from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging.config
import discord
import sys

from mob.logger.logging_config import LOGGING_CONFIG
from mob.logger.logger import get_logger
from mob.models import ConfigRepository
from mob.app_utils import get_settings
from mob.endpoints.rest.order_endpoint import router as order_router
from mob.endpoints.rest.base_endpoint import router as base_router
from mob.endpoints.discord.order_event import OrderDiscordClient

logging.config.dictConfig(LOGGING_CONFIG)
logger = get_logger("app")

_config_repo: ConfigRepository | None = None


def _get_config_repo() -> ConfigRepository:
    global _config_repo
    settings = get_settings()
    if _config_repo is None or _config_repo.source_path != settings.api_config_path:
        _config_repo = ConfigRepository(settings.api_config_path)
    return _config_repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MOB API ready (log level: %s)", get_settings().log_level)
    yield


# Init FastAPI app
app = FastAPI(
    title="MOB API",
    description="Generic action execution API driven by api_config.json definitions.",
    version="0.1.0",
    lifespan=lifespan,
)
# Include routers for FastAPI app
app.include_router(base_router, prefix="")
app.include_router(order_router, prefix="/order")

# Init Discord client
intents = discord.Intents.default()
intents.message_content = True
app_discord = OrderDiscordClient(intents=intents)


def main_api():
    import uvicorn
    # Run FastAPI app with Uvicorn
    logger.info("Starting MOB as REST API")
    uvicorn.run(
        "src.mob.app:app",
        host="0.0.0.0",
        port=8000,
        # reload=True
    )


def main_discord():
    # Include events for Discord client
    logger.info("Starting MOB as Discord Bot")
    app_discord.run(get_settings().discord_bot_token)


if __name__ == "__main__":

    param1 = sys.argv[1] if len(sys.argv) > 1 else "api"

    match param1:

        case "api":

            main_api()

        case "discord":

            main_discord()

        case _:

            logger.error("Invalid parameter. Use 'api' or 'discord'.")
