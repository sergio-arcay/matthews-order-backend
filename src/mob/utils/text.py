import ast
import re

from mob.logger.logger import get_logger


logger = get_logger("utils.text")


ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def remove_ansi(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", text)


def str_to_python(text: str) -> object:
    """Convert a string representation of a Python literal to the corresponding Python object."""
    try:
        return ast.literal_eval(str(text))
    except Exception as e:
        logger.error("Error al convertir en python literal la cadena:", e)
