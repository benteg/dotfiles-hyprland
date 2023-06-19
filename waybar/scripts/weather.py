from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from enum import Enum
from time import sleep
from typing import Any, Callable, Optional, TextIO

import click
import requests

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def interrupt_decorator(handler) -> Callable:
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                handler()
                exit()

        return wrapper

    return decorator


class Unit(Enum):
    STANDARD = "standard"
    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass
class ValueWithSymbol:
    value: Any
    symbol: str

    def __str__(self) -> str:
        return f"{self.value}{self.symbol}"


@dataclass
class Temperature(ValueWithSymbol):
    unit: Unit

    def __str__(self) -> str:
        if self.unit == Unit.METRIC:
            self.symbol = "°C"
        elif self.unit == Unit.IMPERIAL:
            self.symbol = "°F"
        elif self.unit == Unit.STANDARD:
            self.symbol = "K"
        return f"{self.value}{self.symbol}"


@dataclass
class Weather:
    api_key: str
    location: str
    unit: Unit
    error = None
    error_message = None
    css_class = "regular"

    def get(self) -> Optional[dict[Any, Any]]:
        """Request data from the OpenWeather API."""
        try:
            response = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.api_key}&units={self.unit.value}"
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as HErr:
            self.error = "Http Error"
            self.error_message = str(HErr)
        except requests.exceptions.ConnectionError as CErr:
            self.error = "Connection Error"
            self.error_message = str(CErr)
        except requests.exceptions.Timeout as TErr:
            self.error = "Timeout Error"
            self.error_message = str(TErr)
        except requests.exceptions.RequestException as RErr:
            self.error = "Request Exception"
            self.error_message = str(RErr)

    def refresh(self) -> None:
        data: Optional[dict[Any, Any]] = self.get()
        if not data:
            return

        if not data["cod"] == 200:
            self.error = f"Error: {data['cod']}"
            self.error_message = (
                f"{data['message'] if data['message'] else 'Something went wrong'}"
            )
            return

        general_data = data["weather"][0]
        temperature_data = data["main"]
        wind_data = data["wind"]

        self.refreshed_at = datetime.datetime.now().strftime("%H:%M")
        self.city = data.get("name")
        self.datetime = datetime.datetime.fromtimestamp(data.get("dt", float)).strftime(
            "%H:%M"
        )
        self.temperature = Temperature(
            value=round(temperature_data.get("temp")),
            symbol="",
            unit=self.unit,
        )
        if self.temperature.value <= 10:
            self.css_class = "cold"
        elif self.temperature.value > 19:
            self.css_class = "warm"
        elif self.temperature.value > 29:
            self.css_class = "hot"
        self.temperature_feel = Temperature(
            value=round(temperature_data.get("feels_like")),
            symbol="",
            unit=self.unit,
        )
        self.temperature_min = Temperature(
            value=round(temperature_data.get("temp_min")),
            symbol="",
            unit=self.unit,
        )
        self.temperature_max = Temperature(
            value=round(temperature_data.get("temp_max")),
            symbol="",
            unit=self.unit,
        )
        self.humidity = ValueWithSymbol(
            value=temperature_data.get("humidity"),
            symbol="%",
        )
        self.pressure = ValueWithSymbol(
            value=temperature_data.get("pressure"),
            symbol=" hPa",
        )
        self.wind = ValueWithSymbol(
            value=round(wind_data.get("speed")),
            symbol="m/s",
        )
        self.gust = ValueWithSymbol(
            value=round(wind_data.get("gust", "--")),
            symbol="m/s",
        )
        self._wind_direction: int = wind_data.get("deg") // 45 % 8
        self._wind_direction_symbol = [
            "↑",
            "↗",
            "→",
            "↘",
            "↓",
            "↙",
            "←",
            "↖",
        ][self._wind_direction]
        self._wind_direction_value = [
            "N",
            "NE",
            "E",
            "SE",
            "S",
            "SW",
            "W",
            "NW",
        ][self._wind_direction]
        self.wind_direction = ValueWithSymbol(
            value=self._wind_direction_value,
            symbol=self._wind_direction_symbol,
        )
        self.weather: str = general_data.get("main")
        self.weather_desc: str = general_data.get("description").title()
        self.weather_icon: str = {
            "Thunderstorm": " ",
            "Drizzle": " ",
            "Rain": " ",
            "Snow": "  ",
            "Clear": " ",
            "Clouds": "  ",
        }[self.weather]

    def formatter(
        self,
        title_format: str,
        text_format: str,
    ) -> None:
        """Replace the format options with data.

        Args:
            title_format (str): Format to use for the title, for example: title_format = "{city} {temperature}"
            text_format (str): Format to use for the text, for example: text_format = "humidity: {humidity}\npressure: {pressure}"
        """
        if self.error:
            self.text = self.error
            self.tooltip = self.error_message
            return

        format_options = {
            "{city}": self.city,
            "{humidity}": self.humidity.__str__(),
            "{pressure}": self.pressure.__str__(),
            "{temperature}": self.temperature.__str__(),
            "{temperatureFeel}": self.temperature_feel.__str__(),
            "{temperatureMin}": self.temperature_min.__str__(),
            "{temperatureMax}": self.temperature_max.__str__(),
            "{time}": self.datetime,
            "{refreshedAt}": self.refreshed_at,
            "{weather}": self.weather,
            "{weatherIcon}": self.weather_icon,
            "{weatherDesc}": self.weather_desc,
            "{windDirection}": self.wind_direction.__str__(),
            "{windSpeed}": self.wind.__str__(),
            "{windGust}": self.gust.__str__(),
        }

        for opt in format_options:
            title_format = title_format.replace(opt, format_options.get(opt, None))
            text_format = text_format.replace(opt, format_options.get(opt, ""))

        self.text = title_format
        self.tooltip = text_format

    def print(
        self,
        out_format: bool,  # True is output as text, False is output as json
    ) -> None:
        """Replace format options with data and print text and tooltip as json or normal text"""
        if out_format is True:
            print(
                self.text,
                self.tooltip,
                sep="\n",
                flush=True,
            )

        else:
            print(
                json.dumps(
                    {
                        "text": self.text,
                        "tooltip": self.tooltip,
                        "class": self.css_class,
                    }
                ),
                flush=True,
            )


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--api-key",
    "-a",
    help="API key to use for the request.",
    metavar="KEY",
)
@click.option(
    "--config",
    "-c",
    help="Path to config file.",
    type=click.File("r"),
)
@click.option(
    "--interval",
    "-i",
    help="Refresh interval; set to 0 to get weather and exit. [default: 0]",
    type=int,
    metavar="SECONDS",
)
@click.option(
    "--location",
    "-l",
    help="Location to get the weather for",
    metavar="CITY",
)
@click.option(
    "--unit",
    "-u",
    help="Which unit to use. standard: Kelvin(K), metric: Celsius(°C), imperial: Fahrenheit(°C). [default: metric]",
    type=click.Choice([unit.value for unit in Unit], case_sensitive=False),
)
@click.option(
    "--text/--json",
    "-t/-j",
    "out_format",
    is_flag=True,
    help="Print output as plain text or in json format. [default: json]",
)
@click.option(
    "--title-format",
    help="Specify format for title. [default: {temperature}]",
    type=str,
    metavar="FORMAT",
)
@click.option(
    "--text-format",
    help="Specify format for text. [default: {city}]",
    type=str,
    metavar="FORMAT",
)
@interrupt_decorator(lambda: print("Interrupted!\nexiting..."))
def main(
    config: TextIO,  # type: ignore
    api_key: str,  # type: ignore
    location: str,  # type: ignore
    unit: str,  # type: ignore
    interval: int,
    title_format: str,
    text_format: str,
    out_format: bool,
) -> None:
    # Get parameters
    # flags are used over config
    # no flag or config results in fallback value
    if config:
        config: dict[str, Any] = json.load(config)
    else:
        config = {}
    if not api_key:
        if not (api_key := config.get("api_key")):
            raise click.ClickException("Please provide an API-key")
    if not location:
        if not (location := config.get("location")):
            raise click.ClickException("Please provide a location")
    if not unit:
        unit = config.get("units", "metric")
    if interval is None:
        interval = config.get("interval", 0)
    if not title_format:
        title_format = config.get("title_format", "{temperature}")
    if not text_format:
        text_format = config.get("text_format", "{city}")
    if out_format is None:
        out_format = config.get("out_format", False)

    weather = Weather(api_key=api_key, location=location, unit=Unit(unit))
    while True:
        weather.refresh()
        weather.formatter(
            title_format=title_format,
            text_format=text_format,
        )
        weather.print(out_format)
        if interval == 0:
            exit()
        sleep(interval)


if __name__ == "__main__":
    main()
