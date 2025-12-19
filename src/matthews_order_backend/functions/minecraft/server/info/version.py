from __future__ import annotations

from typing import Any, Dict
import asyncio

from matthews_order_backend.utils.text import remove_ansi
from src.matthews_order_backend.functions import FUNCTION_OUTPUT_MESSAGE_MODES
DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.EXECUTION


COMMAND = "rcon-cli version"


async def _check_container_running(container: str) -> bool:
    """ Verify if the docker container is running """
    proc = await asyncio.create_subprocess_exec(
        "docker", "inspect", "-f", "{{.State.Running}}", container,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() == "true"


async def _exec_command_in_container(container: str, command: str) -> str:
    """ Execute a command inside a docker container """
    proc = await asyncio.create_subprocess_exec(
        "docker", "exec", container, "sh", "-c", command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Error ejecutando comando en el contenedor: {stderr.decode().strip()}")
    return stdout.decode().strip()


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the Minecraft server version by executing the appropriate command inside the Docker container.
    """
    container = environment.get("target_container")
    if not container:
        raise ValueError("Missing 'target_container' parameter in configuration.")

    # Check if the docker container exists into this host and is running
    if not await _check_container_running(container):
        raise RuntimeError(f"El contenedor '{container}' no está en ejecución o no existe.")

    # Execute the command into the container
    command = COMMAND.format()
    # Ejecutamos dos veces el comando version ya que la primera ejecución a veces no devuelve nada
    await _exec_command_in_container(container, command)
    result = await _exec_command_in_container(container, command)
    result = remove_ansi(result)

    return {
        "message": f"El resultado de la orden fue: \"{result}\"",
    }
