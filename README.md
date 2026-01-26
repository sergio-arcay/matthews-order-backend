MOB - Matthews Order Backend
======================

Backend para orquestar acciones automatizadas a partir de una configuración declarativa (`api_config.json`). Puede exponerse como API REST (FastAPI) o como bot de Discord que decide qué acción ejecutar con ayuda de un LLM. Incluye funciones listas para usar (Minecraft, utilidades de pruebas, scraping, conversación) y soporte para varios proveedores de IA (Gemini, OpenAI, OpenRouter, G4F).

Características clave
---------------------
- Orquestación declarativa: cada acción se describe en `api_config.json` con función objetivo, entorno, timeout y passkey opcional.
- Dos interfaces de entrada: REST (`/order`) y bot de Discord (prefijo `!` o canal `matthew`).
- Selección de acción con LLM: el bot pide a un modelo elegir la acción y construir el payload según la configuración cargada.
- Ejecución aislada de funciones: carga dinámica desde `src/functions/*`, con soporte async/sync y timeouts.
- Soporte multi-LLM: Gemini, OpenAI, OpenRouter y G4F para selección de acción y conversación.
- Preparado para Docker: imagen ligera con Poetry y Docker CLI para ejecutar órdenes en contenedores (por ejemplo, administración de servidores Minecraft).

Requisitos previos
------------------
- Python 3.13+
- Poetry
- Docker y acceso al socket de Docker (varias funciones y la imagen lo necesitan)
- Claves de los proveedores de IA que vayas a usar (Gemini, OpenAI, OpenRouter, G4F)
- Token del bot de Discord si usas la integración

Variables de entorno
--------------------
Define un `.env` siguiendo `example.env`. Las claves disponibles están en `src/settings.py`:
- `DISCORD_BOT_TOKEN`: token del bot de Discord.
- `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPEN_ROUTER_API_KEY`, `G4F_API_BASE_URL`, `G4F_API_KEY`: credenciales de IA.
- `API_CONFIG_PATH`: ruta al `api_config.json` (por defecto, la raíz del proyecto). Monta el archivo dentro del contenedor si usas Docker.
- `DEFAULT_TIMEOUT`: timeout por defecto en segundos si una acción no define `_timeout`.
- `LOG_LEVEL`: nivel de logging Python (ej. `DEBUG`, `INFO`).

Formato de `api_config.json`
----------------------------
Ejemplo reducido (ver `example.api_config.json` y el real `api_config.json`):
```json
{
  "test-slow-echo": {
    "_passkey": "testkey",          // Opcional: requerido en la petición
    "_timeout": 10,                 // Opcional: override del timeout global
    "function": "testing.slow_echo",// Ruta dentro de functions
    "environment": {},              // Parámetros fijos para la función
    "meta": {                       // Libre para documentar e información extra para el llm
      "description": "Echo con retardo",
      "mandatory_payload_fields": {},
      "optional_payload_fields": {"delay": "Segundos de espera"}
    }
  }
}
```
Cada función debe exponer `run(*, environment, payload) -> dict` y puede declarar `DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE` (ver funciones existentes).

Instalación y ejecución con Poetry
----------------------------------
1) Instala dependencias:
```bash
poetry install
```
2) Exporta o crea tu `.env` (copiando `example.env`) y tu `api_config.json` (usando como base `example.api_config.json`).
3) Arranca la API REST:
```bash
poetry run api
# Servirá en http://0.0.0.0:8000 (scripts definidos en pyproject.toml)
```
4) Arranca el bot de Discord (requiere `DISCORD_BOT_TOKEN`):
```bash
poetry run discord
```
5) Tests:
```bash
poetry run pytest
```

Ejecución con Docker
--------------------
- Construye la imagen:
```bash
docker build -t mob .
```
- Con `docker-compose` (lanza API y bot):
```bash
docker-compose up -d
```
  - La API se expone en `8000`.
  - Se monta `./api_config.json` en `/app/api_config.json`.
  - Se monta `/var/run/docker.sock` para permitir a las funciones ejecutar comandos en contenedores.
  - Sobrescribe timeouts, niveles de log o rutas via variables o `.env`.
- Ejemplo de contenedor único para la API:

Uso de la API REST
------------------
- Healthcheck: `GET /healthz` -> `{"status": "ok"}`.
- Ejecutar acción: `POST /order`
```bash
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{
        "action": "test-slow-echo",
        "passkey": "testkey",
        "payload": {"delay": 2}
      }'
```
- Respuesta (`OrderResponse`):
```json
{
  "action": "test-slow-echo",
  "status": "success",
  "result": {"message": "El echo ha vuelto después de 2.0 segundos."},
  "duration_ms": 2012.345
}
```
Errores comunes: `401` (passkey), `404` (acción no definida), `504` (timeout). Si el `api_config.json` es inválido o falta la función, se devuelve `500`.
- En `http_requests/*.http` tienes ejemplos listos para el cliente HTTP de JetBrains/VS Code.

Bot de Discord
--------------
- Activo con `poetry run discord`.
- Escucha mensajes que:
  - Empiezan por `!` (ej. `!tps`, `!Añade la IP 1.2.3.4 al servidor de minecraft`), o
  - Se envían en un canal llamado `matthew`.
- Flujo:
  1. Construye un prompt con la configuración completa (`get_total_config_file`) y pide a OpenRouter (ahora por defecto) que seleccione la acción y genere el payload (`AI_PROMPT_SELECT_ACTION`).
  2. Ajusta el entorno de la acción con extras del modelo (ej. `confidence`, `message`).
  3. Si el canal es `matthew` y `enable_conversation_context` está activo, añade el histórico reciente al payload.
  4. Ejecuta la función y devuelve `result["message"]` al canal. Si `DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE` es `EXECUTION`, envía primero el mensaje corto generado por la IA.
- Acción por defecto de conversación: `functions/assistant/talk.py`, que combina un system prompt base con la configuración y usa Gemini con fallback a OpenRouter para responder como una conversación general.

Arquitectura y módulos
----------------------
- `src/app.py`: punto de entrada. Crea FastAPI con lifespan y enruta `/healthz` y `/order`. El modo `discord` inicializa el cliente `OrderDiscordClient`.
- `src/settings.py`: configuración con `pydantic-settings`, lectura opcional de `.env` (cuando `IS_DOCKER_CONTAINER` es falso).
- `src/app_utils.py`: cachea settings y `ConfigRepository`, limpia `_` campos sensibles al mostrar config, ejecuta funciones sync/async, y expone `reset_runtime_state` para tests.
- Modelos (`src/models/*`):
  - `actions.py`: `ActionConfig` (timeout, passkey, entorno, función), `OrderRequest/Response`, `ConfigRepository` (recarga `api_config.json` cuando cambia) y `FunctionRegistry` (importa dinámicamente desde `functions`).
  - `ai/*`: `ActionSelectionRequest/Result` (parsea JSON del LLM con `utils.json`), `TalkRequest/Result`.
- Endpoints REST (`src/endpoints/rest/*`):
  - `base_endpoint.py`: `/healthz`.
  - `order_endpoint.py`: valida passkey, resuelve función, aplica timeout (`asyncio.wait_for`), normaliza errores HTTP.
- Bot de Discord (`src/endpoints/discord/order_event.py`): flujo descrito arriba; usa `FUNCTION_OUTPUT_MESSAGE_MODES` para modular los mensajes.
- Clientes de IA (`src/ai/*`):
  - `openai_client.py`, `gemini_client.py`, `open_router_client.py`, `g4f_client.py` comparten helpers (`_build_client`, `_flatten_message_content`) y exponen `select_action` y `talk`.
- Funciones (`src/functions/*`):
  - `assistant/talk.py`: conversación general, inserta prompts de sistema y usa Gemini -> OpenRouter como fallback.
  - `minecraft/server/info/{is_available,tps,version,playing_list}.py`: consultas vía `docker exec` y comandos `rcon-cli`.
  - `minecraft/server/whitelist/{add_ip,remove_ip}.py`: gestión de whitelist vía `rcon-cli`.
  - `testing/{slow_echo,docker_touch}.py`: utilidades para probar timeouts y conectividad Docker.
  - Cada módulo puede fijar `DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE` (`ASSISTANT` o `EXECUTION`) para que el bot decida cómo responder.
- Utilidades (`src/utils/*`): limpieza de ANSI en logs de comandos (`text.py`), parseo robusto de JSON devuelto por LLMs (`json.py`).
- Logging (`src/logger/*`): configuración dictConfig y helper `get_logger`.
- Peticiones de ejemplo (para funcionalidad Endpoints de JetBrains): `http_requests/*.http`.
- Tests: `tests/test_app.py` cubre validaciones del endpoint `/order`. Falta cobertura para el resto de partes.

Notas y buenas prácticas
------------------------
- Protege `api_config.json` y `.env` (contienen passkeys y tokens). No los incluyas en el control de versiones.
- Las funciones que usan Docker requieren montar el socket y que el contenedor objetivo exista; los comandos fallan con `RuntimeError` si no está en ejecución.
- Ajusta `_timeout` por acción para operaciones largas (ej. scraping o conversación).
- Para añadir acciones nuevas: crea un módulo en `src/functions/...` con `run(*, environment, payload)` y regístralo en `api_config.json` con su entorno y passkey si aplica.
