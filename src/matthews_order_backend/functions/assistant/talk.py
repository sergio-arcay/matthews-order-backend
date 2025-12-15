from __future__ import annotations

from typing import Any, Dict

from src.matthews_order_backend.logger.logger import get_logger
from src.matthews_order_backend.models.ai.talk_request import TalkRequest
from src.matthews_order_backend.models.ai.talk_result import TalkResult
from src.matthews_order_backend.functions import FUNCTION_OUTPUT_MESSAGE_MODES
DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.ASSISTANT

from src.matthews_order_backend.ai import (
    talk_to_open_router,
)


logger = get_logger("matthews_order_backend.functions.assistant.talk")


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """ Function to handle 'talk' action.

    When a message is already provided via the environment, it simply returns that message and skips the rest of the
    tasks. This is useful for cases where the action selector has already generated a valid response message and it is
    not necessary to perform any additional processing.

    When no message is provided, it uses a configured LLM client to generate a response based on the user's inputs.
    """
    if environment.get("message"):
        logger.debug("Using pre-existing message from environment.")
        return {
            "message": environment["message"],
        }

    logger.debug("Generating message using LLM client.")
    conversation = payload.get("conversation", [])
    if not conversation:
        if environment.get("system_prompt"):
            conversation.append({"role": "system", "content": environment["system_prompt"]})
        conversation.append({"role": "user", "content": payload.get("message", "")})

    talk_request = TalkRequest(
        model=environment.get("model"),
        conversation=conversation,
    )
    talk_result: TalkResult = talk_to_open_router(talk_request)
    return {
        "message": talk_result.message,
    }
