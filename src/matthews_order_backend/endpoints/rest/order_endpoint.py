import asyncio
import time
import logging

from fastapi import APIRouter, HTTPException, status
from src.matthews_order_backend.models import OrderRequest, OrderResponse, FunctionRegistry
from src.matthews_order_backend.app_utils import execute_callable, get_settings, get_config_repo


logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "",
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
        actions = get_config_repo().get_actions()
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
