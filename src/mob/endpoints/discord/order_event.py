import importlib
import discord
import asyncio
import time

from mob.logger.logger import get_logger
from mob.models import OrderResponse, FunctionRegistry
from mob.models.ai import ActionSelectionRequest
from mob.app_utils import execute_callable, get_settings, get_config_repo, get_total_config_file
from mob.functions import FUNCTION_OUTPUT_MESSAGE_MODES
from mob.ai import (
    select_action_with_open_router,
)

logger = get_logger("endpoints.discord.order_event")

MESSAGE_METADATA_TAG_IN_CONVERSATION = "$$$"

AI_PROMPT_SELECT_ACTION = """
Tu eres Matthew. Ahora vas a trabajar como asistente en un grupo de chat. Tienes que asignar una acción a los mensajes 
que te vayan diciendo los usuarios. Solo puedes escoger y usar las acciones definidas en esta configuración:

{actions_config_json}

Muy importante: responde SIEMPRE con un JSON válido del tipo:

{{"action":"<key_de_accion>",
 "payload":{{...}},
 "confidence":0.X,
 "message":"Respuesta corta al usuario previa a mostrar el resultado existoso. Solo hay una excepción: si la acción es
 una simple conversación, como en el caso de la acción "talk", deja este campo vacio."
}}

Obviamente la acción debe ser la que mejor encaje con la petición y debes recoger y rellenar todos los campos para el
payload. Y recalco, no añadas nada fuera del JSON o rompes el sistema...
"""


class OrderDiscordClient(discord.Client):

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):

        if message.author == self.user:
            return None

        # Check if the message starts with '!' or belongs to a "matthew" channel
        if message.content.startswith('!') or message.channel.name == "matthew":
            await OrderDiscordClient.execute_order(self, message)
            return None

        return None

    @staticmethod
    async def execute_order(self, message: discord.Message) -> OrderResponse | None:
        try:
            # Get action configurations from the repository
            actions = get_config_repo().get_actions()
        except (FileNotFoundError, ValueError) as exc:
            logger.exception("Configuration error while loading api_config.json.")
            await message.channel.send("Hay un error en la configuración que me dió Sam. Me hablas cuando lo arregle.")
            return None
        message_content = message.content.lstrip('!').strip()  # Remove leading '!' and whitespaces
        conversation = []
        system_prompt = AI_PROMPT_SELECT_ACTION.format(actions_config_json=get_total_config_file())

        try:
            action, payload, extras = await OrderDiscordClient.select_action_ai(message_content, system_prompt=system_prompt)
            payload["conversation"] = conversation

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

        # Fill the environment with extras from AI selection
        for key, value in extras.items():
            action_config.environment[key] = value

        # Si es un canal "matthew", usamos todos los mensajes del canal como contexto para la conversación
        # Si es solo un mensaje con prefijo '!', será un mensaje-respuesta individual
        if message.channel.name == "matthew" and action_config.environment.get("enable_conversation_context"):
            async for channel_message in message.channel.history(limit=action_config.environment.get("maximum_message_history", 5)):
                # Añade fecha, hora y autor al mensaje formateado
                formatted_message =\
                    f"{MESSAGE_METADATA_TAG_IN_CONVERSATION}{channel_message.created_at.strftime('%Y-%m-%d %H:%M:%S')} {channel_message.author.name}{MESSAGE_METADATA_TAG_IN_CONVERSATION} {channel_message.content}"
                conversation.append(
                    {"role": "user" if channel_message.author != self.user else "assistant", "content": formatted_message})
            conversation.reverse()

        try:
            handler = FunctionRegistry.resolve(action_config.function)
            handler_module = importlib.import_module(handler.__module__)
            handler_message_mode = getattr(handler_module, "DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE", None)
        except RuntimeError as exc:
            logger.exception("Failed to resolve function for action %s", action)
            await message.channel.send("Algo le falta por programar a Sam. Avisadle de que hay una acción sin una función implementada.")
            return None

        # Si la acción devuelve como mensaje un command output, enviamos el mensaje introductorio
        if handler_message_mode == FUNCTION_OUTPUT_MESSAGE_MODES.EXECUTION:
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
            await message.channel.send(f"No tengo ni idea de que ha fallado, pero ha dado un error genérico al ejecutar la función asociada a la acción '{action}'.")
            return None

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info("Action '%s' executed in %.2f ms", action, duration_ms)
        result_message = result.get("message")

        # Elimina el MESSAGE_METADATA_TAG_IN_CONVERSATION si lo tiene
        if result_message and MESSAGE_METADATA_TAG_IN_CONVERSATION in result_message:
            parts = result_message.split(MESSAGE_METADATA_TAG_IN_CONVERSATION)
            result_message = parts[-1].strip()

        await message.channel.send(result_message)
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
    async def select_action_ai(message_content: str, system_prompt: str = None) -> tuple[str, dict, dict]:
        """ Select action and payload based on AI interpretation of message content. """
        request = ActionSelectionRequest(
            message=message_content,
            system_prompt=system_prompt,
        )
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, select_action_with_open_router, request)
        return result.action, result.payload, result.extras
