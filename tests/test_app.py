from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from src.matthews_order_backend.app import app
from src.matthews_order_backend.app_utils import reset_runtime_state


@contextmanager
def build_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: Dict[str, Any]):
    """Writes a temporary config file and yields a FastAPI TestClient."""
    config_path = tmp_path / "api_config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("API_CONFIG_PATH", str(config_path))
    reset_runtime_state()
    with TestClient(app) as client:
        yield client
    reset_runtime_state()


def test_execute_order_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "add-ip": {
            "passkey": "",
            "timeout": 5,
            "function": "minecraft.server.whitelist.add_ip",
            "parameters": {"target_container": "mc-server"},
        }
    }

    with build_client(tmp_path, monkeypatch, config) as client:
        response = client.post("/order", json={"action": "add-ip", "payload": {"ip": "10.0.0.9"}})

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["ip"] == "10.0.0.9"
    assert body["result"]["container"] == "mc-server"
    assert body["status"] == "success"


def test_execute_order_requires_passkey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "secure-add": {
            "passkey": "letmein",
            "timeout": 5,
            "function": "minecraft.server.whitelist.add_ip",
            "parameters": {"target_container": "mc-server"},
        }
    }

    with build_client(tmp_path, monkeypatch, config) as client:
        unauthorized = client.post("/order", json={"action": "secure-add", "payload": {"ip": "1.2.3.4"}})
        assert unauthorized.status_code == 401

        authorized = client.post(
            "/order",
            json={"action": "secure-add", "payload": {"ip": "1.2.3.4"}, "passkey": "letmein"},
        )

    assert authorized.status_code == 200
    assert authorized.json()["result"]["ip"] == "1.2.3.4"


def test_execute_order_unknown_action(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "add-ip": {
            "passkey": "",
            "timeout": 5,
            "function": "minecraft.server.whitelist.add_ip",
            "parameters": {"target_container": "mc-server"},
        }
    }

    with build_client(tmp_path, monkeypatch, config) as client:
        response = client.post("/order", json={"action": "non-existing"})

    assert response.status_code == 404


def test_execute_order_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "slow-task": {
            "passkey": "",
            "timeout": 0.1,
            "function": "testing.slow_echo",
            "parameters": {},
        }
    }

    with build_client(tmp_path, monkeypatch, config) as client:
        response = client.post("/order", json={"action": "slow-task", "payload": {"delay": 0.5}})

    assert response.status_code == 504


def test_execute_order_propagates_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "add-ip": {
            "passkey": "",
            "timeout": 5,
            "function": "minecraft.server.whitelist.add_ip",
            "parameters": {"target_container": "mc-server"},
        }
    }

    with build_client(tmp_path, monkeypatch, config) as client:
        response = client.post("/order", json={"action": "add-ip"})

    assert response.status_code == 400
    assert "payload.ip" in response.json()["detail"]


def test_invalid_config_returns_500(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "api_config.json"
    config_path.write_text("not a json", encoding="utf-8")
    monkeypatch.setenv("API_CONFIG_PATH", str(config_path))
    reset_runtime_state()

    with TestClient(app) as client:
        response = client.post("/order", json={"action": "anything"})

    assert response.status_code == 500
