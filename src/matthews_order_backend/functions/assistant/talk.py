from __future__ import annotations

from typing import Any, Dict

from src.matthews_order_backend.logger.logger import get_logger
from src.matthews_order_backend.functions import FUNCTION_OUTPUT_MESSAGE_MODES
DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.ASSISTANT


logger = get_logger("matthews_order_backend.functions.assistant.talk")


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """ Function to handle 'talk' action.  Currently, this function assumes that the response message is provided
    from the action selector task using the environment object, and simply echoes it back.
    """
    message = environment.get("message") or "Lo siento, todavía no puedo hablar con tanta libertad..."
    return {
        "message": message,
    }
