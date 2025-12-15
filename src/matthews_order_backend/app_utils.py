from functools import lru_cache, partial
from typing import Any, Callable
from pathlib import Path
import inspect
import asyncio
import json
import os

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
    """Helper to read the entire config file as a string.

    TODO: Remove 'passkey' fields from config sections before returning.

    """
    config_repo = get_config_repo()
    if not config_repo.source_path or not config_repo.source_path.exists():
        raise FileNotFoundError("Configuration file not found.")
    # Read the json file
    with open(config_repo.source_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    # Remove 'sensitive' fields: those starting with '__'
    def remove_sensitive_fields(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                key: remove_sensitive_fields(value)
                for key, value in obj.items()
                if not key.startswith("__")
            }
        elif isinstance(obj, list):
            return [remove_sensitive_fields(item) for item in obj]
        else:
            return obj
    cleaned_data = remove_sensitive_fields(json_data)
    return json.dumps(cleaned_data, indent=2)


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    # Load environment variables from .env file if not in Docker
    is_docker_container = os.getenv("IS_DOCKER_CONTAINER", "false").lower() == "true"
    if not is_docker_container:
        from dotenv import load_dotenv
        load_dotenv()
    # Build settings from the rest of environment variables
    api_config_path = Path(os.getenv("API_CONFIG_PATH", "")) or None
    default_timeout = float(os.getenv("DEFAULT_TIMEOUT", None))
    log_level = os.getenv("LOG_LEVEL", None)
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", None)
    gemini_api_key = os.getenv("GEMINI_API_KEY", None)
    openai_api_key = os.getenv("OPENAI_API_KEY", None)
    open_router_api_key = os.getenv("OPEN_ROUTER_API_KEY", None)
    g4f_api_base_url = os.getenv("G4F_API_BASE_URL", None)
    g4f_api_key = os.getenv("G4F_API_KEY", None)
    return Settings(
        is_docker_container=is_docker_container,
        api_config_path=api_config_path,
        default_timeout=default_timeout,
        log_level=log_level,
        discord_bot_token=discord_bot_token,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        open_router_api_key=open_router_api_key,
        g4f_api_base_url=g4f_api_base_url,
        g4f_api_key=g4f_api_key,
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
