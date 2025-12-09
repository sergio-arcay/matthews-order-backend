import inspect
import asyncio
import os
from pathlib import Path
from typing import Any, Callable
from functools import lru_cache, partial

from src.matthews_order_backend.models import FunctionRegistry, ConfigRepository
from src.matthews_order_backend.settings import Settings


_config_repo: ConfigRepository | None = None


@lru_cache(maxsize=1)
def _get_config_repo() -> ConfigRepository:
    global _config_repo
    settings = get_settings()
    if _config_repo is None or _config_repo.source_path != settings.api_config_path:
        _config_repo = ConfigRepository(settings.api_config_path)
    return _config_repo


def get_config_repo() -> ConfigRepository:
    return _get_config_repo()


def get_total_config_file() -> str:
    """Helper to read the entire config file as a string."""
    config_repo = get_config_repo()
    if not config_repo.source_path or not config_repo.source_path.exists():
        raise FileNotFoundError("Configuration file not found.")
    return config_repo.source_path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    api_config_path = Path(os.getenv("API_CONFIG_PATH", "")) or None
    default_timeout = float(os.getenv("DEFAULT_TIMEOUT", None))
    log_level = os.getenv("LOG_LEVEL", None)
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", None)
    return Settings(
        api_config_path=api_config_path,
        default_timeout=default_timeout,
        log_level=log_level,
        discord_bot_token=discord_bot_token
    )


def get_settings() -> Settings:
    return _get_settings()


def _build_function_kwargs(func: Callable[..., Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Map the allowed keyword arguments for the target function."""
    sig = inspect.signature(func)
    kwargs: dict[str, Any] = {}
    if "environment" in sig.parameters:
        kwargs["environment"] = payload["environment"]
    if "payload" in sig.parameters:
        kwargs["payload"] = payload["payload"]
    if not kwargs:
        # When the function does not declare expected keywords, send them anyway.
        kwargs = payload
    return kwargs


async def execute_callable(
    func: Callable[..., Any], *, environment: dict[str, Any], payload: dict[str, Any]
) -> Any:
    """Executes the resolved callable honoring sync + async implementations."""
    invocation_payload = {"environment": environment, "payload": payload}
    kwargs = _build_function_kwargs(func, invocation_payload)

    if inspect.iscoroutinefunction(func):
        return await func(**kwargs)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, **kwargs))


def reset_runtime_state() -> None:
    """Helper for tests: clears cached settings, config repo, and imports."""
    global _config_repo
    _get_settings.cache_clear()
    _config_repo = None
    FunctionRegistry.clear()
