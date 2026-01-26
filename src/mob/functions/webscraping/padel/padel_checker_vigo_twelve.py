from __future__ import annotations
from datetime import datetime
from typing import Any, Dict
import time

from mob.autoweb.awengines import AWEngineBase, awe_pipeline, AWEngineResponse
from mob.autoweb.webscraper import WebScraperFactory
from mob.autoweb.aiagent import AIAgent
from mob.functions import FUNCTION_OUTPUT_MESSAGE_MODES

DEFAULT_FUNCTION_OUTPUT_MESSAGE_MODE = FUNCTION_OUTPUT_MESSAGE_MODES.EXECUTION


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:

    response = Autoweb().run(
        engine=AWEnginePadelCheckerVigoTwelve,
        args={
            "username": "arcay.sergio@gmail.com",
            "password": "l1oBKGkZjK",
            "dates_to_check": ["2026-01-25", "2026-01-26"],
        },
    )

    return "WIP"


class AWEnginePadelCheckerVigoTwelve(AWEngineBase):

    def __init__(self, **kwargs):
        mandatory_kwargs = ["username", "password", "dates_to_check"]
        settings = {
            "base_url": "https://reservas.twelvepadelzenter.com/Web/index.php",
        }
        super().__init__(settings=settings, mandatory_kwargs=mandatory_kwargs, **kwargs)

    @awe_pipeline
    def pipeline(self, dir_downloads: str = None):
        ai_agent = AIAgent(provider="open_router")
        webscraper = WebScraperFactory.create(self.base_url, dir_downloads=dir_downloads, default_agent=ai_agent)
        webscraper.navigate(url=self.base_url)  # Navega a la URL base y espera 4 segundos
        webscraper.input_write(selector="input#email", text=self.username)
        webscraper.input_write(selector="input#password", text=self.password)
        webscraper.click(selector="button[type='submit']")
        webscraper.navigate(url="https://reservas.twelvepadelzenter.com/Web/schedule.php")
        time.sleep(5)
        days_index = [self.__calc_day_index_from_today(day_to_check) for day_to_check in self.dates_to_check]
        for day_index in days_index:
            webscraper.screenshot(selector=f"div#reservations table.reservations:nth-of-type({day_index})")
        return AWEngineResponse.DOWNLOADING, {}

    def __calc_day_index_from_today(self, date_to_check: str) -> int:
        today = datetime.today()
        check_date = datetime.strptime(date_to_check, "%Y-%m-%d")
        delta_days = (check_date.date() - today.date()).days
        return delta_days + 1  # +1 porque el índice empieza en 1
