from typing import Any

from pydantic import BaseModel, Field


class TalkResult(BaseModel):
    """Standardized result returned by AI providers after a talk interaction."""

    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
