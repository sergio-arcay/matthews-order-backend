from typing import Iterable

from google import genai
from google.genai import types
from openai import OpenAI as Gemini

from mob.app_utils import get_settings
from mob.logger.logger import get_logger
from mob.models.ai import (
    ActionSelectionRequest,
    ActionSelectionResult,
    TalkRequest,
    TalkResult,
)

logger = get_logger("ai.gemini_client")

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _build_client(api_key: str | None) -> Gemini:
    # Let the SDK read from the environment when an explicit key is not provided.
    if api_key:
        return Gemini(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key,
        )
    return Gemini()


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


def select_action(request: ActionSelectionRequest, *, client: genai.Client | None = None) -> ActionSelectionResult:
    """Ask Gemini to choose an action given a user message."""
    settings = get_settings()
    client = client or _build_client(api_key=settings.gemini_api_key)

    model_name = request.model or DEFAULT_GEMINI_MODEL
    logger.debug("Selecting action with Gemini model %s", model_name)

    response = client.models.generate_content(
        model=model_name,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            system_instruction=request.system_prompt,
        ),
        contents=[request.message],
    )
    response_text = response.text
    logger.debug("Gemini response: %s", response_text)
    return ActionSelectionResult.from_response_text(response_text)


def talk(request: TalkRequest, *, client: Gemini | None = None) -> TalkResult:
    """Have a conversation with a Gemini model given a TalkRequest."""
    settings = get_settings()
    api_key = settings.gemini_api_key
    client = client or _build_client(api_key=api_key)

    model_name = request.model or DEFAULT_GEMINI_MODEL
    logger.debug("Talking with Gemini model %s", model_name)

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
        raise ValueError("Empty response from Gemini client.")

    logger.debug("Gemini response: %s", response_text)
    return TalkResult(message=response_text, metadata={})
