from __future__ import annotations

from typing import Any, Dict
import requests
import asyncio
import socket

from src.matthews_order_backend.functions import FUNCTION_OUTPUT_MESSAGE_MODES
DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.EXECUTION


COMMAND = None


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


async def _is_server_reachable(ip, puerto=25565):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.settimeout(5)  # Tiempo máximo de espera: 5 segundos
        result = sock.connect_ex((ip, puerto))
        return result == 0
    finally:
        sock.close()


async def _get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json').json()
        return response['ip']
    except Exception:
        return None


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if the Minecraft server is available and reachable.
    """
    container = environment.get("target_container")
    if not container:
        raise ValueError("Missing 'target_container' parameter in configuration.")
    ip_address_server = environment.get("ip_address_server")
    if not ip_address_server:
        ip_address_server = await _get_public_ip()
        if not ip_address_server:
            raise ValueError("No se ha podido determinar la IP pública del servidor. Proporciónala en payload.ip_address_server.")
    port_server = environment.get("port_server")
    if not port_server:
        port_server = 25565  # Puerto por defecto de Minecraft

    is_container_running = await _check_container_running(container)
    is_server_reachable = await _is_server_reachable(ip_address_server, port_server)

    message = f"El servidor de Minecraft está {'en ejecución' if is_container_running else 'detenido'} "
    if is_container_running and is_server_reachable:
        message += f"y es accesible desde la dirección {ip_address_server}:{port_server}. "
    elif is_container_running and not is_server_reachable:
        message += f"pero detecto problemas de conexión desde la dirección {ip_address_server}:{port_server}. "

    return {
        "message": message,
    }
