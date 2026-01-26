from openai import OpenAI as OpenRouter
from typing import Iterable

from mob.app_utils import get_settings
from mob.logger.logger import get_logger
from mob.models.ai import (
    ActionSelectionRequest,
    ActionSelectionResult,
    TalkRequest,
    TalkResult,
)

logger = get_logger("ai.open_router_client")

DEFAULT_OPEN_ROUTER_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"


def _build_client(api_key: str | None) -> OpenRouter:
    # Let the SDK read from the environment when an explicit key is not provided.
    if api_key:
        return OpenRouter(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
    return OpenRouter()


def _flatten_message_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)
    return ""


def select_action(request: ActionSelectionRequest, *, client: OpenRouter | None = None) -> ActionSelectionResult:
    """Ask OpenRouter to choose an action given a user message."""
    settings = get_settings()
    client = client or _build_client(api_key=settings.open_router_api_key)

    model_name = request.model or DEFAULT_OPEN_ROUTER_MODEL
    logger.debug("Selecting action with OpenRouter model %s", model_name)

    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
    )
    choice = response.choices[0].message if response.choices else None
    response_text = _flatten_message_content(choice.content) if choice else ""

    if not response_text:
        raise ValueError("Empty response from OpenRouter.")

    logger.debug("OpenRouter response: %s", response_text)
    return ActionSelectionResult.from_response_text(response_text)


def talk(request: TalkRequest, *, client: OpenRouter | None = None) -> TalkResult:
    """ Have a conversation with an OpenRouter model given a TalkRequest.
    """
    settings = get_settings()
    api_key = settings.open_router_api_key
    client = client or _build_client(api_key=api_key)

    model_name = request.model or DEFAULT_OPEN_ROUTER_MODEL
    logger.debug("Talking with OpenRouter model %s", model_name)

    messages = []
    for msg in request.conversation:
        messages.append({"role": msg.role, "content": msg.content})

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
    )
    choice = response.choices[0].message if response.choices else None
    response_text = _flatten_message_content(choice.content) if choice else ""

    if not response_text:
        raise ValueError("Empty response from OpenRouter client.")

    logger.debug("OpenRouter response: %s", response_text)
    return TalkResult(message=response_text, metadata={})
