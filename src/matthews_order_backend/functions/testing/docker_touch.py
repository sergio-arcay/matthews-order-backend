from __future__ import annotations

import asyncio
from typing import Any, Dict
import uuid


async def _check_container_running(container: str) -> bool:
    # Verifica si el contenedor está en ejecución
    proc = await asyncio.create_subprocess_exec(
        "docker", "inspect", "-f", "{{.State.Running}}", container,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() == "true"


async def run(*, parameters: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    container = parameters.get("target_container")
    if not container:
        raise ValueError("Missing 'target_container' parameter.")

    # Comprobación de que el contenedor existe y está en ejecución
    if not await _check_container_running(container):
        raise RuntimeError(f"El contenedor '{container}' no está en ejecución o no existe.")

    # Ruta temporal única dentro del contenedor
    temp_filename = f"test_touch_file_{uuid.uuid4().hex}.txt"
    temp_path = f"/tmp/{temp_filename}"

    # Comando para crear el archivo
    proc = await asyncio.create_subprocess_exec(
        "docker", "exec", container, "touch", temp_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Error creando archivo en el contenedor: {stderr.decode().strip()}")

    return {
        "action": "docker_touch",
        "container": container,
        "path": temp_path,
        "stdout": stdout.decode().strip(),
    }
