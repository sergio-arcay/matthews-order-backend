import re

ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')


def remove_ansi(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub('', text)
