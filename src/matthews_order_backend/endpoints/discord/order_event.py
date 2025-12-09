from google.genai import types
from google import genai
import discord
import asyncio
import time
import json

from src.matthews_order_backend.logger.logger import get_logger
from src.matthews_order_backend.models import OrderResponse, FunctionRegistry
from src.matthews_order_backend.app_utils import execute_callable, get_settings, get_config_repo, get_total_config_file


logger = get_logger("matthews_order_backend.endpoints.discord.order_event")

AI_INPUT_PROMPT = """
Ey Matthew! Que tal?! Ahora vas a tener que asignar una acción a cada mensaje de usuario. Solo puedes usar las acciones
definidas en esta configuración que te he hecho:

{actions_config_json}

Importante porfa: responde SIEMPRE con un JSON válido:

{{"action":"<key_de_accion>",
 "payload":{{...}},
 "confidence":0.X,
 "message":"Respuesta muy corta al usuario previa a mostrar el resultado existoso. Puedes decirle lo que te de la gana
 pero haciendo referencia a que va a recibir ahora el resultado de la acción. Se creativo, que aquí estamos para
 entretenernos entre colegas."
}}

Obviamente la acción debe ser la que mejor encaje con la petición y debes recoger y rellenar todos los campos para el
payload. Y en serio, porfa, no añadas nada fuera del JSON o petas mi backend...
"""


class OrderDiscordClient(discord.Client):

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):

        if message.author == self.user:
            return None

        if message.content.startswith('!'):
            await OrderDiscordClient.execute_order(message)
            return None

        return None

    @staticmethod
    async def execute_order(message: discord.Message) -> OrderResponse | None:
        try:
            # Get action configurations from the repository
            actions = get_config_repo().get_actions()
        except (FileNotFoundError, ValueError) as exc:
            logger.exception("Configuration error while loading api_config.json.")
            await message.channel.send("Hay un error en la configuración que me dió Sam. Me hablas cuando lo arregle.")
            return None
        message_content = message.content.lstrip('!').strip()  # Remove leading '!' and whitespaces
        system_prompt = AI_INPUT_PROMPT.format(actions_config_json=get_total_config_file())

        try:
            action, payload, extras = OrderDiscordClient.select_action_ai(message_content, system_prompt=system_prompt)
            # TODO: use extras.confidence
        except ValueError as exc:
            await message.channel.send("Creo que hubo un error interpretando tu mensaje. Repítelo por favor.")
            return None
        except Exception as exc:
            logger.exception("AI processing failed for message: %s", message_content)
            await message.channel.send("Estoy durmiendo ya... Háblame mañana o molesta a un humano si es urgente.")
            return None

        action_config = actions.get(action)
        if not action_config:
            await message.channel.send(f"No tengo ni idea de lo que me estás pidiendo. Si estás seguro de que puedo hacerlo, ¿puedes reformular tu mensaje?")
            return None

        try:
            handler = FunctionRegistry.resolve(action_config.function)
        except RuntimeError as exc:
            logger.exception("Failed to resolve function for action %s", action)
            await message.channel.send("Algo le falta por programar a Sergio. Avisadle de que hay una acción sin una función implementada.")
            return None

        await message.channel.send(extras.get("message"))
        timeout = action_config.resolved_timeout(get_settings().default_timeout)
        started = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                execute_callable(handler, environment=action_config.environment, payload=payload),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await message.channel.send(f"La acción '{action}' ha tardado demasiado y la he cancelado. Inténtalo de nuevo si quieres pero es posible que haya algún error interno.")
            return None
        except ValueError as exc:
            await message.channel.send(f"Lo siento. No tengo ni idea de que ha fallado, pero parece que la función asociada a la acción '{action}' ha recibido datos inválidos.")
            return None
        except Exception as exc:
            logger.exception("Action '%s' failed with an unexpected error.", action)
            await message.channel.send(f"No tengo ni siquiera una mínima pista de que ha fallado, pero ha dado un error genérico al ejecutar la función asociada a la acción '{action}'.")
            return None

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info("Action '%s' executed in %.2f ms", action, duration_ms)
        await message.channel.send(f"Tengo el siguiente resultado: {result["message"]}")
        return None

    @staticmethod
    def select_action(message_content: str) -> tuple[str, dict, dict]:
        """ Select action and payload based on message content.

        Each pair of words is treated as a key-value pair for the payload:

            !action key1 value1 key2 value2

        """
        parts = message_content.split()
        action = parts[0]
        payload = {}
        for i in range(1, len(parts), 2):
            key = parts[i]
            value = parts[i + 1] if i + 1 < len(parts) else ""
            payload[key] = value
        return action, payload, dict()

    @staticmethod
    def select_action_ai(message_content: str, model: str = "gemini-2.5-flash", system_prompt: str = None) -> tuple[str, dict, dict]:
        """ Select action and payload based on AI interpretation of message content.

        The client gets the API key from the environment variable `GEMINI_API_KEY`.
        """

        def _loads_json_safe(s: str) -> dict:
            """ Attempt to load JSON from a string, returning an empty dict on failure. Supports ```json ... ``` format.
            """
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
            # Attempt to extract JSON from markdown code block
            if s.startswith("```") and s.endswith("```"):
                s = s.strip()[7:-3].strip()
                try:
                    return json.loads(s)
                except json.JSONDecodeError:
                    pass
            raise ValueError("Input is not valid JSON.")

        client = genai.Client()
        logger.debug(f"Selecting action with AI model {model} for message: {message_content}")
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),  # Disables thinking
                system_instruction=system_prompt,
            ),
            contents=[message_content],
        )
        response_text = response.text
        logger.debug(f"AI response: {response_text}")
        try:
            response_json = _loads_json_safe(response_text)
            action = response_json.get("action")
            payload = response_json.get("payload", {})
            extras = {
                "confidence": response_json.get("confidence", 0),
                "message": response_json.get("message", "")
            }
            return action, payload, extras
        except ValueError as exc:
            logger.exception("Failed to parse AI response: %s", response_text)
            raise ValueError("Failed to parse AI response as JSON.") from exc
