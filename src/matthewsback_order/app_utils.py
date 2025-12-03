import inspect
import asyncio
import dotenv
from pathlib import Path
from typing import Any, Callable
from functools import lru_cache, partial

from src.matthewsback_order.models import FunctionRegistry
from src.matthewsback_order.settings import Settings


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    # Get Path object from environment
    api_config_path = Path(dotenv.get_key(dotenv.find_dotenv(), "API_CONFIG_PATH") or "") or None
    default_timeout = float(dotenv.get_key(dotenv.find_dotenv(), "DEFAULT_TIMEOUT") or 15.0) or 15.0
    log_level = dotenv.get_key(dotenv.find_dotenv(), "LOG_LEVEL") or "INFO"
    return Settings(api_config_path=api_config_path, default_timeout=default_timeout, log_level=log_level)


def get_settings() -> Settings:
    return _get_settings()


def _build_function_kwargs(func: Callable[..., Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Map the allowed keyword arguments for the target function."""
    sig = inspect.signature(func)
    kwargs: dict[str, Any] = {}
    if "parameters" in sig.parameters:
        kwargs["parameters"] = payload["parameters"]
    if "payload" in sig.parameters:
        kwargs["payload"] = payload["payload"]
    if not kwargs:
        # When the function does not declare expected keywords, send them anyway.
        kwargs = payload
    return kwargs


async def execute_callable(
    func: Callable[..., Any], *, parameters: dict[str, Any], payload: dict[str, Any]
) -> Any:
    """Executes the resolved callable honoring sync + async implementations."""
    invocation_payload = {"parameters": parameters, "payload": payload}
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
