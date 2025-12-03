from __future__ import annotations

import asyncio
import logging
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status

from src.matthewsback_order.models import OrderRequest, OrderResponse, FunctionRegistry, ConfigRepository
from src.matthewsback_order.app_utils import execute_callable, get_settings

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


@app.post(
    "/order",
    response_model=OrderResponse,
    summary="Execute a configured action",
    responses={
        400: {"description": "Invalid payload"},
        401: {"description": "Passkey mismatch"},
        404: {"description": "Unknown action"},
        504: {"description": "Action timed out"},
    },
)
async def execute_order(request: OrderRequest) -> OrderResponse:
    try:
        # Get action configurations from the repository
        actions = _get_config_repo().get_actions()
    except (FileNotFoundError, ValueError) as exc:
        logger.exception("Configuration error while loading api_config.json.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    action_config = actions.get(request.action)
    if not action_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action '{request.action}' is not configured.",
        )

    if action_config.passkey:
        if request.passkey != action_config.passkey:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid passkey.",
            )

    try:
        handler = FunctionRegistry.resolve(action_config.function)
    except RuntimeError as exc:
        logger.exception("Failed to resolve function for action %s", request.action)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    payload = request.payload or {}
    timeout = action_config.resolved_timeout(get_settings().default_timeout)
    started = time.perf_counter()

    try:
        result = await asyncio.wait_for(
            execute_callable(handler, parameters=action_config.parameters, payload=payload),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Action '{request.action}' timed out after {timeout} seconds.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Action '%s' failed with an unexpected error.", request.action)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Action failed to execute.",
        ) from exc

    duration_ms = (time.perf_counter() - started) * 1000
    return OrderResponse(
        action=request.action,
        status="success",
        result=result,
        duration_ms=round(duration_ms, 3),
    )


@app.get("/healthz", summary="Health probe")
async def healthz() -> dict[str, str]:
    """Simple health endpoint used by orchestration platforms."""
    return {"status": "ok"}


def main():
    import uvicorn
    uvicorn.run("src.matthewsback_order.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":

    main()
