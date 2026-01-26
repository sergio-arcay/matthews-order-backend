from pydantic import BaseModel, Field


class ActionSelectionRequest(BaseModel):
    """Typed input for asking an LLM to choose the right action."""

    message: str = Field(..., description="Raw message sent by the user.")
    system_prompt: str | None = Field(
        default=None,
        description="Optional system prompt to prepend to the conversation.",
    )
    model: str | None = Field(
        default=None,
        description="Optional override for the provider default model.",
    )
