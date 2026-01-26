from __future__ import annotations
from typing import Any, Callable, Dict
from pydantic import BaseModel, Field
from pathlib import Path
import importlib
import threading
import json


# region Constants

DEFAULT_FUNCTION_NAME = "run"
FUNCTIONS_PACKAGE = "functions"

# endregion


class ActionConfig(BaseModel):
    """Describes how to execute an action defined inside api_config.json."""

    _passkey: str | None = None
    _timeout: float | None = None
    function: str
    environment: Dict[str, Any] = Field(default_factory=dict)

    def resolved_timeout(self, fallback: float) -> float:
        return self._timeout or fallback


class OrderRequest(BaseModel):
    """Incoming payload for a /order request."""

    action: str = Field(..., description="Name of the action to execute.")
    passkey: str | None = Field(
        default=None, description="Optional secret required by some ai."
    )
    payload: Dict[str, Any] | None = Field(
        default=None,
        description="Runtime payload forwarded to the target function.",
    )


class OrderResponse(BaseModel):
    """Standardized response for a successful order."""

    action: str
    status: str
    result: Any
    duration_ms: float


class ConfigRepository:
    """Lazy loader + cache for api_config.json."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self._cached_actions: dict[str, ActionConfig] | None = None
        self._cache_mtime: float | None = None
        self._lock = threading.Lock()

    def _read_from_disk(self) -> dict[str, ActionConfig]:
        if not self.source_path.exists():
            raise FileNotFoundError(
                f"api_config.json not found at {self.source_path!s}"
            )

        try:
            raw_data = json.loads(self.source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("api_config.json contains invalid JSON.") from exc
        if not isinstance(raw_data, dict):
            raise ValueError("api_config.json must contain a JSON object at the root.")

        actions: dict[str, ActionConfig] = {}
        for action_name, action_payload in raw_data.items():
            if not isinstance(action_payload, dict):
                raise ValueError(
                    f"Action '{action_name}' must be defined with an object value."
                )
            actions[action_name] = ActionConfig(**action_payload)

        return actions

    def get_actions(self) -> dict[str, ActionConfig]:
        """
        Returns every configured action, refreshing the cache only when the file
        changes on disk.
        """
        try:
            mtime = self.source_path.stat().st_mtime
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"api_config.json not found at {self.source_path!s}"
            ) from exc

        with self._lock:
            if (
                self._cached_actions is None
                or self._cache_mtime is None
                or mtime != self._cache_mtime
            ):
                self._cached_actions = self._read_from_disk()
                self._cache_mtime = mtime

            return self._cached_actions


class FunctionRegistry:
    """Caches imports for action callables."""

    _cache: dict[str, Callable[..., Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def resolve(cls, target: str) -> Callable[..., Any]:
        with cls._lock:
            if target not in cls._cache:
                cls._cache[target] = cls._import_target(target)
            return cls._cache[target]

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._cache.clear()

    @staticmethod
    def _import_target(target: str) -> Callable[..., Any]:
        module_path, attr_name = _split_function_target(target)
        dotted_path = f"{FUNCTIONS_PACKAGE}.{module_path}"
        try:
            module = importlib.import_module(dotted_path)
        except ImportError as exc:
            raise RuntimeError(f"Cannot import module '{dotted_path}'.") from exc

        try:
            return getattr(module, attr_name)
        except AttributeError as exc:
            raise RuntimeError(
                f"Callable '{attr_name}' not found in module '{dotted_path}'."
            ) from exc


# region Utils

def _split_function_target(target: str) -> tuple[str, str]:
    """
    Splits the configured function string into module + attribute parts. When an
    attribute is not provided, defaults to 'run'.
    """
    if ":" in target:
        module_path, attr_name = target.rsplit(":", 1)
    else:
        module_path, attr_name = target, DEFAULT_FUNCTION_NAME

    return module_path, attr_name

# endregion
