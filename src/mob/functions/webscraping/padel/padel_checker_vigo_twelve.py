from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict
import asyncio
import time

from autoweb.spatially.analyzers.availability_window_analyzer import AvailabilityWindowAnalyzer
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
        "data": result.data,
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
        days_index = [(day_to_check, self.__calc_day_index_from_today(day_to_check)) for day_to_check in self.dates_to_check]
        days_index = [di for di in days_index if 0 < di[1] <= 6]  # Filtra índices válidos
        if not days_index:
            return AWEngineResponse.EMPTY, {}
        # Extrae las pistas disponibles
        schema_json = self.__build_spatially_schema_json()
        total_extracted_data = {}
        for di_str, dii in days_index:
            screenshot_path = webscraper.screenshot(selector=f"div#reservations table.reservations:nth-of-type({dii})")
            extracted_data = (AvailabilityWindowAnalyzer.from_payload(schema_json)
                              .analyze(str(screenshot_path))
                              .to_dict(include_cells=True))
            total_extracted_data[di_str] = self.__process_extracted_data(extracted_data)

        return AWEngineResponse.DOWNLOADING, total_extracted_data

    def __calc_day_index_from_today(self, date_to_check: str) -> int:
        """ Calcula el índice del día a partir de hoy (1 = hoy, 2 = mañana, etc.), sin importar la hora, solo el
        cambio de día.
        """
        today = datetime.today()
        check_date = datetime.strptime(date_to_check, "%Y-%m-%d")
        delta_days = (check_date.date() - today.date()).days
        return delta_days + 1  # +1 porque el índice empieza en 1


    def __build_spatially_schema_json(self) -> dict:

        cell_time_labels = [
            "09:00-09:30", "09:30-10:00", "10:00-10:30", "10:30-11:00", "11:00-11:30", "11:30-12:00",
            "12:00-12:30", "12:30-13:00", "13:00-13:30", "13:30-14:00", "14:00-14:30", "14:30-15:00",
            "15:00-15:30", "15:30-16:00", "16:00-16:30", "16:30-17:00", "17:00-17:30", "17:30-18:00",
            "18:00-18:30", "18:30-19:00", "19:00-19:30", "19:30-20:00", "20:00-20:30", "20:30-21:00",
            "21:00-21:30", "21:30-22:00", "22:00-22:30", "22:30-23:00", "23:00-23:30", "23:30-00:00"
        ]

        return {
            "name": "pistas-twelve-vigo",
            "description": "Esquema espacial para analizar la disponibilidad de pistas de pádel en Twelve Vigo, con 12"
                           "pistas (1-12) y franjas horarias de 30 minutos desde las 09:00 hasta las 00:00.",
            "config": {
                "sample_mode": "majority",
                "sample_radius": 10,
                "tolerance": 18,
                "clamp_coords": True,
                "window_span": 3,
                "coords_step": [93, 0],
                "default_colormap": {
                    "#FFFFFF": True,
                    "#D9D9D9": False
                }
            },
            "data": [
                *[{"label": f"1-{l}",  **({"coords": [437, 62]}  if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"2-{l}",  **({"coords": [437, 102]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"3-{l}",  **({"coords": [437, 142]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"4-{l}",  **({"coords": [437, 182]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"5-{l}",  **({"coords": [437, 222]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"6-{l}",  **({"coords": [437, 262]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"7-{l}",  **({"coords": [437, 302]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"8-{l}",  **({"coords": [437, 342]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"9-{l}",  **({"coords": [437, 382]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"10-{l}", **({"coords": [437, 422]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"11-{l}", **({"coords": [437, 462]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
                *[{"label": f"12-{l}", **({"coords": [437, 502]} if i == 0 else {}) } for i, l in enumerate(cell_time_labels)],
            ]
        }

    def __process_extracted_data(self, extracted_data):
        """
        Para cda elemento de la lista extracted_data[available_windows] extrae la información de la pista, la hora de
        inicio y calcula la hora de fin sumando hora y media a la de inicio. Devuelve una lista de diccionarios en el
        que la key sea el numero de la pista en string y el valor un listado de timestamps con las horas de inicio y fin
        de cada ventana disponible.

        Los elementos de available_windows tienen la forma:

            {'end_index': 2, 'end_label': '1-10:00-10:30', 'start_index': 0, 'start_label': '1-09:00-09:30'}

        La función unicamente usa start_label para extraer la información. start-label tiene el formato: "N-HH:MM-HH:MM"
        donde N es el número de pista, HH:MM es la hora de inicio y HH:MM es la hora de fin. La función extrae el número
        de pista directamente de N y la franja de horas como la hora de inicio + 1 hora y media (90 minutos). La hora
        de fin propia de la label se ignora completamente, ya que solo marca la franja de una celda del horario, no de
        la ventana completa (cada ventana son 3 celdas).
        """
        result = {}
        available_windows = extracted_data.get("available_windows", [])
        for window in available_windows:
            start_label = window.get("start_label", "")
            try:
                pista, hora_inicio, _ = start_label.split("-")
                dt_inicio = datetime.strptime(hora_inicio, "%H:%M")
                dt_fin = dt_inicio + timedelta(minutes=90)
                inicio_str = dt_inicio.strftime("%H:%M")
                fin_str = dt_fin.strftime("%H:%M")
                if pista not in result:
                    result[pista] = []
                result[pista].append({"start": inicio_str, "end": fin_str})
            except Exception as e:
                pass
        return result
