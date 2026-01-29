from typing import Iterable

from openai import OpenAI as Client

from mob.app_utils import get_settings
from mob.logger.logger import get_logger
from mob.models.ai import (
    ActionSelectionRequest,
    ActionSelectionResult,
    TalkRequest,
    TalkResult,
)

logger = get_logger("ai.g4f_client")

DEFAULT_G4F_MODEL = "gpt-3.5-turbo"


def _build_client(api_base_url: str | None = None, *, api_key: str | None = None) -> Client:
    if api_key:
        return Client(
            api_key=api_key,
            base_url=api_base_url,
        )
    return Client()


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


def select_action(request: ActionSelectionRequest, *, client: Client | None = None) -> ActionSelectionResult:
    """Ask G4F to choose an action given a user message."""
    settings = get_settings()
    api_base_url = settings.g4f_api_base_url
    api_key = settings.g4f_api_key
    client = client or _build_client(api_base_url=api_base_url, api_key=api_key)

    model_name = request.model or DEFAULT_G4F_MODEL
    logger.debug("Selecting action with G4F model %s", model_name)

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
        raise ValueError("Empty response from G4F client.")

    logger.debug("G4F response: %s", response_text)
    return ActionSelectionResult.from_response_text(response_text)


def talk(request: TalkRequest, *, client: Client | None = None) -> TalkResult:
    """Have a conversation with G4F given a TalkRequest."""
    settings = get_settings()
    api_base_url = settings.g4f_api_base_url
    api_key = settings.g4f_api_key
    client = client or _build_client(api_base_url=api_base_url, api_key=api_key)

    model_name = request.model or DEFAULT_G4F_MODEL
    logger.debug("Talking with G4F model %s", model_name)

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
        raise ValueError("Empty response from G4F client.")

    logger.debug("G4F response: %s", response_text)
    return TalkResult(message=response_text, metadata={})
