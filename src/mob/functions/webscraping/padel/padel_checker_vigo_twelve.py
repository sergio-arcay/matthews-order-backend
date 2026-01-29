from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import asyncio
import time

from autoweb.awengines.awe_base import AWEngineBase, AWEngineResponse, awe_pipeline
from autoweb.webscraper.webscraper import WebScraperFactory
from autoweb.autoweb import Autoweb

from mob.functions import FUNCTION_OUTPUT_MESSAGE_MODES
from mob.utils.text import str_to_python

DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.EXECUTION


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:

    username = environment.get("username")
    password = environment.get("password")

    dates_to_check = str_to_python(payload.get("dates_to_check", "[]"))
    if not dates_to_check:
        raise ValueError("payload.dates_to_check is required to check availability.")

    result = await asyncio.to_thread(
        Autoweb().run,
        engine=AWEnginePadelCheckerVigoTwelve,
        args={
            "username": username,
            "password": password,
            "dates_to_check": dates_to_check,
        }
    )

    return {
        "message": f"Se ha completado la comprobación de disponibilidad para las fechas: {dates_to_check}.",
        "files": result.files,
    }


class AWEnginePadelCheckerVigoTwelve(AWEngineBase):

    def __init__(self, **kwargs):
        mandatory_kwargs = ["username", "password", "dates_to_check"]
        settings = {
            "base_url": "https://reservas.twelvepadelzenter.com/Web/index.php",
        }
        super().__init__(settings=settings, mandatory_kwargs=mandatory_kwargs, **kwargs)

    @awe_pipeline
    def pipeline(self, dir_downloads: str = None):
        # Define un nuevo WebScraper
        webscraper = WebScraperFactory.create(self.base_url, dir_downloads=dir_downloads)
        # Abre la URL BASE
        webscraper.navigate(url=self.base_url)  # Navega a la URL base y espera 4 segundos
        # Introduce las credenciales
        webscraper.input_write(selector="input#email", text=self.username)
        webscraper.input_write(selector="input#password", text=self.password)
        # Click en el botón de login
        webscraper.click(selector="button[type='submit']")
        # Abre la URL del Scheduler
        webscraper.navigate(url="https://reservas.twelvepadelzenter.com/Web/schedule.php")
        # Wait
        time.sleep(5)
        # Calcula el índice del día a comprobar
        days_index = [self.__calc_day_index_from_today(day_to_check) for day_to_check in self.dates_to_check]
        days_index = [di for di in days_index if 0 < di <= 6]  # Filtra índices válidos
        if not days_index:
            return AWEngineResponse.EMPTY, {}
        # Extrae las pistas disponibles
        for day_index in days_index:
            webscraper.screenshot(selector=f"div#reservations table.reservations:nth-of-type({day_index})")
        return AWEngineResponse.DOWNLOADING, {}

    def __calc_day_index_from_today(self, date_to_check: str) -> int:
        today = datetime.today()
        check_date = datetime.strptime(date_to_check, "%Y-%m-%d")
        delta_days = (check_date.date() - today.date()).days
        return delta_days + 1  # +1 porque el índice empieza en 1


if __name__ == '__main__':

    response = Autoweb().run(
        engine=AWEnginePadelCheckerVigoTwelve,
        args={
            "username": "arcay.sergio@gmail.com",
            "password": "l1oBKGkZjK",
            "dates_to_check": ["2026-01-30", "2026-01-31"],
        },
    )

    # Abre los paths response.files con el programa por defecto del sistema
    if response.files:
        import subprocess
        import platform
        import os
        if platform.system() == "Windows":
            for file in response.files:
                os.startfile(file)
        elif platform.system() == "Darwin":
            for file in response.files:
                subprocess.call(["open", file])
        else:
            for file in response.files:
                subprocess.call(["xdg-open", file])
