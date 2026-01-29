from pydantic import BaseModel, Field


class MessageAI(BaseModel):
    role: str = Field(
        ...,
        description="Role of the message sender, e.g., 'user', 'assistant', or 'system'.",
    )
    content: str = Field(
        ...,
        description="Content of the message.",
    )


class TalkRequest(BaseModel):
    """
    Standardized request format for AI conversational models.
    """

    conversation: list[MessageAI] = Field(
        ...,
        description="List of messages in the conversation.",
    )
    model: str | None = Field(
        default=None,
        description="Optional override for the provider default model.",
    )
