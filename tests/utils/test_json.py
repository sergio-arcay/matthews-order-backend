from __future__ import annotations
import pytest

from mob.utils import json as json_utils


def test_loads_json_safe_parses_standard_json() -> None:
    assert json_utils.loads_json_safe('{"a": 1}') == {"a": 1}


def test_loads_json_safe_extracts_from_code_block() -> None:
    payload = "```json\n{\"x\": 2}\n```"
    assert json_utils.loads_json_safe(payload) == {"x": 2}


def test_loads_json_safe_repairs_common_llm_artifacts() -> None:
    payload = "{name: 'test', value: 3, trailing: true,}"
    parsed = json_utils.loads_json_safe(payload)
    assert parsed["name"] == "test"
    assert parsed["value"] == 3
    assert parsed["trailing"] is True


def test_loads_json_safe_can_raise_on_failure() -> None:
    with pytest.raises(ValueError):
        json_utils.loads_json_safe("not json", return_empty_on_failure=False)


def test_extract_json_from_llm_response_injects_defaults() -> None:
    response = '{"result": "ok"}'
    parsed = json_utils.extract_json_from_llm_response(response, expected_keys=["result", "meta"], default_values={"meta": {}})
    assert parsed["result"] == "ok"
    assert parsed["meta"] == {}
