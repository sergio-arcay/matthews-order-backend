from typing import Iterable

from openai import OpenAI

from src.matthews_order_backend.models.ai import (
    ActionSelectionRequest,
    ActionSelectionResult,
)
from src.matthews_order_backend.app_utils import get_settings
from src.matthews_order_backend.logger.logger import get_logger


logger = get_logger("matthews_order_backend.ai.openai_client")

DEFAULT_OPENAI_MODEL = "gpt-5-nano"


def _build_client(api_key: str | None) -> OpenAI:
    # Let the SDK read from the environment when an explicit key is not provided.
    if api_key:
        return OpenAI(api_key=api_key)
    return OpenAI()


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


def select_action(request: ActionSelectionRequest, *, client: OpenAI | None = None) -> ActionSelectionResult:
    """Ask OpenAI to choose an action given a user message."""
    settings = get_settings()
    client = client or _build_client(api_key=settings.openai_api_key)

    model_name = request.model or DEFAULT_OPENAI_MODEL
    logger.debug("Selecting action with OpenAI model %s", model_name)

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
        raise ValueError("Empty response from OpenAI.")

    logger.debug("OpenAI response: %s", response_text)
    return ActionSelectionResult.from_response_text(response_text)
