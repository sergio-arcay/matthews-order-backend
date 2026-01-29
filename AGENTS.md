AGENTS Guide
============

Context
-------
- Proyecto: MOB - Matthews Order Backend (FastAPI + bot de Discord) para ejecutar acciones declaradas en `api_config.json`.
- Entry points: `poetry run api` (REST) y `poetry run discord` (bot). Ambos definidos en `pyproject.toml`.
- Código principal: `src/*`; funciones en `functions/`, clientes LLM en `ai/`, endpoints en `endpoints/`.

Configuración y entorno
-----------------------
- Variables en `.env` (ver `example.env`) y esquema en `src/settings.py`: `API_CONFIG_PATH`, `DEFAULT_TIMEOUT`, `LOG_LEVEL`, tokens/keys de IA y `DISCORD_BOT_TOKEN`.
- `api_config.json` es crítico: define acciones, passkeys, timeouts y entornos. No versionar secretos; monta el archivo al contenedor si corres en Docker.
- En Docker, `IS_DOCKER_CONTAINER=true` evita cargar `.env` vía dotenv; monta `/var/run/docker.sock` si las funciones necesitan Docker.

Ejecución
---------
- Local: `poetry install`; `poetry run api` (puerto 8000); `poetry run discord` para el bot.
- Docker: construir `mob`; `docker-compose up -d` levanta API + bot. Volúmenes clave: `./api_config.json:/app/api_config.json` y el socket Docker.
- Salud: `GET /healthz`; órdenes: `POST /order` con `action`, `passkey` (si aplica) y `payload`.

Arquitectura rápida
-------------------
- `app.py`: inicializa FastAPI y Discord client; selecciona modo según arg (`api`/`discord`).
- `endpoints/rest/order_endpoint.py`: valida acción, passkey, timeout y ejecuta función vía `FunctionRegistry` + `execute_callable`.
- `endpoints/discord/order_event.py`: usa LLM (OpenRouter por defecto) para elegir acción y payload; aplica contexto de conversación; respeta `DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE`.
- `ai/*.py`: clientes para Gemini, OpenAI, OpenRouter, G4F; exponen `select_action` y `talk`.
- `functions/*`: acciones reales. Ejemplos: Minecraft (rcon vía `docker exec`), pruebas (`slow_echo`, `docker_touch`), conversación (`assistant/talk`), scraping WIP.
- `utils/json.py`: parseo robusto de respuestas LLM a JSON; `utils/text.py`: limpia ANSI.
- `logger/*`: configuración de logging (stdout).

Pruebas y mantenimiento
-----------------------
- Tests: `poetry run pytest` (ver `tests/test_app.py`).
- Añadir acción: crear módulo con `run(*, environment, payload)` y `DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE`; registrar en `api_config.json`.
- Si cambias `api_config.json`, revisa que los campos `_passkey` y `timeout` estén bien escritos (nota: en ejemplos `timeout`, en código se lee `timeout` pero el modelo expone `resolved_timeout`).

Precauciones
------------
- No eliminar ni exponer `api_config.json` ni `.env`; contienen passkeys y tokens.
- Funciones de Docker fallan si el contenedor no existe o no está corriendo; monta el socket y usa nombres correctos.
- Mantén tiempo de espera suficiente para acciones largas (scraping, conversación) ajustando `timeout` por acción o `DEFAULT_TIMEOUT`.
