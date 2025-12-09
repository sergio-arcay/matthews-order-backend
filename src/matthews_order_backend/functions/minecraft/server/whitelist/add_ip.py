from __future__ import annotations

from typing import Any, Dict
import asyncio


COMMAND = "rcon-cli ipwhitelist add {ip_address}"


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
    Add an IP address to the Minecraft server whitelist.

    Connect to the specified target container and add the given IP address using exec commands.
    """
    container = environment.get("target_container")
    if not container:
        raise ValueError("Missing 'target_container' parameter in configuration.")

    ip_address = payload.get("ip_address")
    if not ip_address:
        raise ValueError("payload.ip_address is required to whitelist a player.")

    # Check if the docker container exists into this host and is running
    if not await _check_container_running(container):
        raise RuntimeError(f"El contenedor '{container}' no está en ejecución o no existe.")

    # Execute the command into the container to add the IP address to the whitelist
    command = COMMAND.format(ip_address=ip_address)
    result = await _exec_command_in_container(container, command)

    return {
        "message": f"Se completó la adición de la IP '{ip_address}' de la whitelist con el siguiente resultado: {result}",
    }
