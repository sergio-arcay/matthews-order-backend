from __future__ import annotations

import asyncio
from typing import Any, Dict


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Utility function leveraged in tests to validate timeout handling.
    Sleeps for `payload.get("delay", 0)` seconds before echoing the payload.
    """
    delay = float(payload.get("delay", 0))
    if delay > 0:
        await asyncio.sleep(delay)
    return {
        "message": f"El echo ha vuelto después de {delay} segundos."
    }
