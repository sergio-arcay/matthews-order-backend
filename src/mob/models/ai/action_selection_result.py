from typing import Any

from pydantic import BaseModel, Field

from mob.utils.json import loads_json_safe


class ActionSelectionResult(BaseModel):
    """Normalized result returned by AI providers when selecting an action."""

    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    message: str = ""

    @property
    def extras(self) -> dict[str, Any]:
        return {"confidence": self.confidence, "message": self.message}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionSelectionResult":
        if not isinstance(data, dict):
            raise ValueError("AI response must be a JSON object.")

        action = data.get("action")
        if not action:
            raise ValueError("AI response missing 'action'.")

        payload = data.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValueError("AI response 'payload' must be a JSON object.")

        confidence_raw = data.get("confidence", 0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, confidence)

        message = data.get("message") or ""

        return cls(
            action=str(action),
            payload=payload,
            confidence=confidence,
            message=str(message),
        )

    @classmethod
    def from_response_text(cls, response_text: str) -> "ActionSelectionResult":
        parsed = loads_json_safe(response_text, return_empty_on_failure=False)
        return cls.from_dict(parsed)
