from __future__ import annotations
import pytest

from pathlib import Path
import json

from mob import app as mob_app
from mob.app_utils import reset_runtime_state

# Tests in this module:
# - test_config_repo_uses_env_path
# - test_config_repo_reuses_cached_instance_until_reset


@pytest.fixture(autouse=True)
def _reset_runtime(
        monkeypatch: pytest.MonkeyPatch
):
    """Ensure cached settings/config repos are cleared between tests."""
    yield
    reset_runtime_state()
    mob_app._config_repo = None
    monkeypatch.delenv("API_CONFIG_PATH", raising=False)


def test_config_repo_uses_env_path(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "api_config.json"
    config_path.write_text(json.dumps({"echo": {"function": "testing.slow_echo"}}), encoding="utf-8")
    monkeypatch.setenv("API_CONFIG_PATH", str(config_path))

    mob_app._config_repo = None
    repo = mob_app._get_config_repo()

    assert repo.source_path == config_path
    assert repo.get_actions()["echo"].function == "testing.slow_echo"


def test_config_repo_reuses_cached_instance_until_reset(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "api_config.json"
    config_path.write_text(json.dumps({"a": {"function": "testing.slow_echo"}}), encoding="utf-8")
    monkeypatch.setenv("API_CONFIG_PATH", str(config_path))

    mob_app._config_repo = None
    first_repo = mob_app._get_config_repo()
    second_repo = mob_app._get_config_repo()
    assert first_repo is second_repo

    # Changing the path only affects new instances after clearing the cached state.
    new_config_path = tmp_path / "other.json"
    new_config_path.write_text(json.dumps({"b": {"function": "testing.slow_echo"}}), encoding="utf-8")
    monkeypatch.setenv("API_CONFIG_PATH", str(new_config_path))
    reset_runtime_state()
    mob_app._config_repo = None

    refreshed_repo = mob_app._get_config_repo()
    assert refreshed_repo is not first_repo
    assert refreshed_repo.source_path == new_config_path
