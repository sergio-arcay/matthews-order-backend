from fastapi import APIRouter

from mob.logger.logger import get_logger

logger = get_logger("endpoints.rest.general")

router = APIRouter()


@router.get("/healthz", summary="Health probe")
async def healthz() -> dict[str, str]:
    """Simple health endpoint used by orchestration platforms."""
    return {"status": "ok"}
