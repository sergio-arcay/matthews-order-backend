from google import genai
from google.genai import types

from src.matthews_order_backend.models.ai import (
    ActionSelectionRequest,
    ActionSelectionResult,
)
from src.matthews_order_backend.app_utils import get_settings
from src.matthews_order_backend.logger.logger import get_logger


logger = get_logger("matthews_order_backend.ai.gemini")

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _build_client(api_key: str | None) -> genai.Client:
    # Let the SDK resolve the key from the environment when not provided.
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()


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
