from mob.ai.open_router_client import select_action as select_action_with_open_router
from mob.ai.gemini_client import select_action as select_action_with_gemini
from mob.ai.openai_client import select_action as select_action_with_openai
from mob.ai.g4f_client import select_action as select_action_with_g4f

from mob.ai.open_router_client import talk as talk_to_open_router
from mob.ai.gemini_client import talk as talk_to_gemini
from mob.ai.openai_client import talk as talk_to_openai
from mob.ai.g4f_client import talk as talk_to_g4f

__all__ = [
    "select_action_with_open_router",
    "select_action_with_gemini",
    "select_action_with_openai",
    "select_action_with_g4f",

    "talk_to_open_router",
    "talk_to_gemini",
    "talk_to_openai",
    "talk_to_g4f",
]
