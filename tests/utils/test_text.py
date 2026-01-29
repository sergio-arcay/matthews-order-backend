from __future__ import annotations
import pytest

from mob.utils.text import remove_ansi


def test_remove_ansi_strips_escape_sequences() -> None:
    text = "\x1b[31mred\x1b[0m plain"
    assert remove_ansi(text) == "red plain"
