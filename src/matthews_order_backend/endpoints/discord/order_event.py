import discord
import logging
import asyncio
import time

from src.matthews_order_backend.models import OrderResponse, FunctionRegistry
from src.matthews_order_backend.app_utils import execute_callable, get_settings, get_config_repo


logger = logging.getLogger(__name__)


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
            await message.channel.send("Hay un error de configuración del servidor.")
            return None
        action, payload = OrderDiscordClient.select_action(message.content)

        action_config = actions.get(action)
        if not action_config:
            await message.channel.send(f"La acción '{action}' no está configurada.")
            return None

        try:
            handler = FunctionRegistry.resolve(action_config.function)
        except RuntimeError as exc:
            logger.exception("Failed to resolve function for action %s", action)
            await message.channel.send("Error interno del servidor al resolver la función.")
            return None

        timeout = action_config.resolved_timeout(get_settings().default_timeout)
        started = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                execute_callable(handler, environment=action_config.environment, payload=payload),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await message.channel.send(f"La acción '{action}' ha excedido el tiempo límite de {timeout} segundos.")
            return None
        except ValueError as exc:
            await message.channel.send(f"La acción '{action}' falló con un error de valor: {str(exc)}")
            return None
        except Exception as exc:
            logger.exception("Action '%s' failed with an unexpected error.", action)
            await message.channel.send(f"La acción '{action}' falló con un error inesperado.")
            return None

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info("Action '%s' executed in %.2f ms", action, duration_ms)
        await message.channel.send(f"Listo! Resultado: {result}")
        return None

    @staticmethod
    def select_action(message_content: str) -> tuple[str, dict]:
        """ Select action and payload based on message content.

        The message must start with '!' followed by the action name. After that, each new pair of words is treated as a
        key-value pair for the payload:

            !action key1 value1 key2 value2

        """
        if not message_content.startswith('!'):
            raise ValueError("Message content must start with '!' to indicate an action.")
        parts = message_content.lstrip('!').split()
        action = parts[0]
        payload = {}
        for i in range(1, len(parts), 2):
            key = parts[i]
            value = parts[i + 1] if i + 1 < len(parts) else ""
            payload[key] = value
        return action, payload
