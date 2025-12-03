from __future__ import annotations

import asyncio
from typing import Any, Dict


async def run(*, parameters: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Utility function leveraged in tests to validate timeout handling.
    Sleeps for `payload.get("delay", 0)` seconds before echoing the payload.
    """
    delay = float(payload.get("delay", 0))
    if delay > 0:
        await asyncio.sleep(delay)
    return {
        "parameters": parameters,
        "payload": payload,
        "message": f"Echoed after {delay} seconds delay.",
    }
