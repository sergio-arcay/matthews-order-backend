from pydantic import BaseModel, Field
from typing import Any


class TalkResult(BaseModel):
    """ Standardized result returned by AI providers after a talk interaction.
    """
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
