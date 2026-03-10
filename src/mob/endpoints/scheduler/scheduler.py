import asyncio
import time

from mob.models import FunctionRegistry, ActionConfig
from mob.logger.logger import get_logger
from mob.app_utils import (
    execute_callable,
    get_config_repo,
    get_settings,
)


DEFAULT_CHECKER_TIMEOUT = 120  # seconds


logger = get_logger("scheduler")

class GeneralScheduler:
    def __init__(self):
        self.periodic_tasks = self._extract_periodic_tasks()

    def _extract_actions_from_repository(self):
        try:
            # Get action configurations from the repository
            return get_config_repo().get_actions()
        except (FileNotFoundError, ValueError):
            logger.exception("Configuration error while loading api_config.json.")
            return []

    def _extract_periodic_tasks(self):
        actions = self._extract_actions_from_repository()
        return [action for action in actions.values() if action.checker_interval]

    def _get_checker(self, action_config: ActionConfig):
        try:
            handler = FunctionRegistry.resolve(action_config.function, checker=True)
        except RuntimeError:
            logger.exception("Failed to resolve checker for action %s", action_config.function)
            return None
        return handler

    def _get_function(self, action_config: ActionConfig):
        try:
            handler = FunctionRegistry.resolve(action_config.function, checker=False)
        except RuntimeError:
            logger.exception("Failed to resolve function for action %s", action_config.function)
            return None
        return handler

    async def _execute_action(self, action_config: ActionConfig):
        function = self._get_function(action_config)
        if not function:
            logger.warning(f"No se pudo resolver el handler para la funcion {action_config.function}. Saltando ejecución.")
            return

        timeout = action_config.resolved_timeout(get_settings().default_timeout)
        started = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                execute_callable(function, environment=action_config.environment, payload={}),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"La funcion '{action_config.function}' ha tardado demasiado y la he cancelado.")
            return None
        except ValueError:
            logger.exception("Value error while executing function '%s'.", action_config.function)
            return None
        except Exception:
            logger.exception("Function '%s' failed with an unexpected error.", action_config.function)
            return None

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info("Action '%s' executed in %.2f ms", action_config.function, duration_ms)

    async def _run_periodic_task(self, action_config: ActionConfig):

        check_func = self._get_checker(action_config)
        if not check_func:
            logger.warning(f"No se pudo obtener el checker para la acción {action_config.function}. Saltando tarea periódica.")
            return

        while True:
            try:
                check_result = await asyncio.wait_for(
                    execute_callable(check_func, environment=action_config.environment, payload={}),
                    timeout=DEFAULT_CHECKER_TIMEOUT,
                )
                if check_result is False:
                    await self._execute_action(action_config)
            except Exception as e:
                logger.error(f"Error ejecutando checker '{action_config.function}': {e}")
            await asyncio.sleep(action_config.checker_interval)

    async def run_async(self):
        tasks = [self._run_periodic_task(cfg) for cfg in self.periodic_tasks]
        if not tasks:
            logger.info("No hay tareas periódicas definidas en api_config.json")
            return
        await asyncio.gather(*tasks)

    def run(self):
        asyncio.run(self.run_async())
