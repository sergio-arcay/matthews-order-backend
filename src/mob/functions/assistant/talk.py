from __future__ import annotations

from typing import Any, Dict

from mob.ai import talk_to_gemini, talk_to_open_router
from mob.app_utils import get_total_config_file
from mob.functions import FUNCTION_OUTPUT_MESSAGE_MODES
from mob.logger.logger import get_logger
from mob.models.ai.talk_request import TalkRequest
from mob.models.ai.talk_result import TalkResult
from mob.prompts import AI_SYSTEM_PROMPT_FUNCTION_TALK
from mob.utils.time import get_current_date, get_current_time

DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.ASSISTANT


logger = get_logger("functions.assistant.talk")


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Function to handle 'talk' action.

    When a message is already provided via the environment, it simply returns that message and skips the rest of the
    tasks. This is useful for cases where the action selector has already generated a valid response message and it is
    not necessary to perform any additional processing.

    When no message is provided, it uses a configured LLM client to generate a response based on the user's inputs.
    """
    conversation = payload.get("conversation", [])
    if not conversation:
        conversation.append({"role": "user", "content": payload.get("message", "")})
    if environment.get("system_prompt"):  # PRIMARY SYSTEM PROMPT
        conversation.insert(0, {"role": "system", "content": environment["system_prompt"]})
    if AI_SYSTEM_PROMPT_FUNCTION_TALK:
        conversation.insert(
            1,
            {
                "role": "system",
                "content": AI_SYSTEM_PROMPT_FUNCTION_TALK.format(
                    current_date=get_current_date(),
                    current_time=get_current_time(),
                    actions_config_json=get_total_config_file(),
                ),
            },
        )

    talk_request = TalkRequest(
        model=environment.get("model"),
        conversation=conversation,
    )
    try:
        talk_result: TalkResult = talk_to_gemini(talk_request)
    except Exception:
        logger.exception("Gemini talk failed, falling back to OpenRouter")
        talk_result = talk_to_open_router(talk_request)
    return {
        "message": talk_result.message,
    }
