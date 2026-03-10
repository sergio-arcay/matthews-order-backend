from __future__ import annotations

from contextlib import asynccontextmanager
import logging.config
import argparse

from fastapi import FastAPI
import discord

from mob.endpoints.rest.order_endpoint import router as order_router
from mob.endpoints.rest.base_endpoint import router as base_router
from mob.endpoints.discord.order_event import OrderDiscordClient
from mob.logger.logging_config import build_logging_config
from mob.logger.logger import get_logger
from mob.models import ConfigRepository
from mob.app_utils import get_settings
from mob.endpoints.scheduler.scheduler import GeneralScheduler

logging.config.dictConfig(build_logging_config(get_settings().log_level))
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


def main_scheduler():
    """
    Instancia y ejecuta el GeneralScheduler.
    """
    scheduler = GeneralScheduler()
    scheduler.run()


def main_api(with_scheduler: bool = False):
    import uvicorn

    # Run FastAPI app with Uvicorn
    logger.info("Starting MOB as REST API")
    if with_scheduler:
        main_scheduler()
    uvicorn.run(
        "src.mob.app:app",
        host="0.0.0.0",
        port=8000,
        # reload=True
    )


def main_discord(with_scheduler: bool = False):
    # Include events for Discord client
    logger.info("Starting MOB as Discord Bot")
    if with_scheduler:
        main_scheduler()
    app_discord.run(get_settings().discord_bot_token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MOB App runner")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    api_parser = subparsers.add_parser("api", help="Ejecuta en modo API REST")
    api_parser.add_argument("--scheduler", action="store_true", help="Activa funciones periódicas (scheduler)")

    discord_parser = subparsers.add_parser("discord", help="Ejecuta en modo Discord Bot")
    discord_parser.add_argument("--scheduler", action="store_true", help="Activa funciones periódicas (scheduler)")

    args = parser.parse_args()

    if args.mode == "api":
        main_api(with_scheduler=args.scheduler)
    elif args.mode == "discord":
        main_discord(with_scheduler=args.scheduler)
    else:
        logger.error("Modo no reconocido. Use 'api' o 'discord'.")
