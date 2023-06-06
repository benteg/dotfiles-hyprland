from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from time import sleep
from typing import Any, Callable, TextIO

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


class Weather:
    """Get and process weather data from the OpenWeather api"""

    def __init__(self, api_key, location, units: Unit):
        self.api_key: str = api_key
        self.location: str = location
        self.units: Unit = units
        self.error = None

    def request(self) -> None:
        """Get weather data form OpenWeather"""
        try:
            return requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.api_key}&units={self.units.value}"
            ).json()
        # In case of error self.text becomes self.error -> see def print()
        # In case of error self.tooltip becomes self.error_tooltip -> see def print()
        except requests.exceptions.HTTPError as HErr:
            self.error = "Http Error"
            self.error_tooltip = str(HErr)
        except requests.exceptions.ConnectionError as CErr:
            self.error = "Connection Error"
            self.error_tooltip = str(CErr)
        except requests.exceptions.Timeout as TErr:
            self.error = "Timeout Error"
            self.error_tooltip = str(TErr)
        except requests.exceptions.RequestException as RErr:
            self.error = "Error"
            self.error_tooltip = str(RErr)

    def get_weather(self, raw_data) -> None:
        """Get weather from API data"""
        if raw_data:
            if raw_data["cod"] == 200:
                self.city = raw_data["name"]
                self.datetime = datetime.fromtimestamp(
                    raw_data["dt"]
                ).strftime("%H:%M")
                self.temperature: float = raw_data["main"]["temp"]
                self.temperature_feel: float = raw_data["main"]["feels_like"]
                self.temperature_min: float = raw_data["main"]["temp_min"]
                self.temperature_max: float = raw_data["main"]["temp_max"]
                if self.units == Unit.METRIC:
                    self.temperature_unit = "°C"
                elif self.units == Unit.IMPERIAL:
                    self.temperature_unit = "°F"
                elif self.units == Unit.STANDARD:
                    self.temperature_unit = " K"
                else:
                    self.temperature_unit = ""
                self.wind_speed = raw_data["wind"]["speed"]
                self.wind_direction = raw_data["wind"]["deg"]
                self.wind_direction_icon = [
                    "↑",
                    "↗",
                    "→",
                    "↘",
                    "↓",
                    "↙",
                    "←",
                    "↖",
                ][self.wind_direction // 45 % 8]
                self.wind_direction_text = [
                    "N",
                    "NE",
                    "E",
                    "SE",
                    "S",
                    "SW",
                    "W",
                    "NW",
                ][self.wind_direction // 45 % 8]
                try:
                    self.wind_gust = raw_data["wind"]["gust"]
                except KeyError:
                    self.wind_gust = None
                self.wind_unit = "m/s"

                self.weather = raw_data["weather"][0]["main"]
                self.weather_desc = raw_data["weather"][0]["description"]
                self.weather_humid = raw_data["main"]["humidity"]
                self.weather_icon = {
                    "Thunderstorm": "",
                    "Drizzle": "",
                    "Rain": "",
                    "Snow": "",
                    "Clear": "",
                    "Clouds": "",
                }[self.weather]
                self.weather_unit = "%"

            else:
                self.error = f"Error: {raw_data['cod']}"
                self.error_tooltip = f"{raw_data['message'] if raw_data['message'] else 'Something went wrong'}"

    def refresh(self) -> None:
        self.get_weather(self.request())

    def print(
        self,
        out_format: bool,  # True is output as text, False is output as json
        title_format: str,
        text_format: str,
    ) -> None:
        """Replace format options with data and print text and tooltip as json or normal text"""
        if self.error:
            if out_format is True:
                if self.error:
                    print(self.error, self.error_tooltip, flush=True)

            else:
                if self.error:
                    print(
                        json.dumps(
                            {"text": self.error, "tooltip": self.error_tooltip}
                        ),
                        flush=True,
                    )

                    print(self.error, self.error_tooltip, flush=True)

                else:
                    if self.error:
                        print(
                            json.dumps(
                                {
                                    "text": self.error,
                                    "tooltip": self.error_tooltip,
                                }
                            ),
                            flush=True,
                        )

        else:
            format_options = {
                "{city}": self.city,
                "{humidity}": f"{round(self.weather_humid, ndigits=1)}{self.weather_unit}",
                "{temperature}": f"{round(self.temperature, ndigits=1)}{self.temperature_unit}",
                "{temperatureFeel}": f"{round(self.temperature_feel, ndigits=1)}{self.temperature_unit}",
                "{temperatureMin}": f"{round(self.temperature_min, ndigits=1)}{self.temperature_unit}",
                "{temperatureMax}": f"{round(self.temperature_max, ndigits=1)}{self.temperature_unit}",
                "{time}": self.datetime,
                "{weather}": self.weather,
                "{weatherIcon}": self.weather_icon,
                "{weatherDesc}": self.weather_desc.title(),
                "{windDirection}": str(self.wind_direction),
                "{windDirectionIcon}": self.wind_direction_icon,
                "{windDirectionText}": self.wind_direction_text,
                "{windSpeed}": f"{round(self.wind_speed)}{self.wind_unit}",
                "{windGust}": f"{round(self.wind_gust)}{self.wind_unit}"
                if self.wind_gust
                else "",
            }
            # Replace format options with data
            for opt in format_options:
                try:
                    title_format = title_format.replace(
                        opt, format_options[opt]
                    )
                    text_format = text_format.replace(opt, format_options[opt])
                except AttributeError:
                    pass
            self.text = title_format
            self.tooltip = text_format

            if out_format is True:
                print(
                    self.text,
                    self.tooltip,
                    sep="\n",
                    flush=True,
                )

            else:
                print(
                    json.dumps({"text": self.text, "tooltip": self.tooltip}),
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
    "--units",
    "-u",
    help="Which units to use. standard: Kelvin(K), metric: Celsius(°C), imperial: Fahrenheit(°C). [default: metric]",
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
    units: str,  # type: ignore
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
        try:
            api_key: str = config["api_key"]
        except KeyError:
            api_key = input("API key: ")
    if not location:
        try:
            location: str = config["location"]
        except KeyError:
            location = input("Location: ")
    if not units:
        try:
            units: str = config["units"]
        except KeyError:
            units = "metric"
    if interval is None:
        try:
            interval = config["interval"]
        except KeyError:
            interval = 0
    if not title_format:
        try:
            title_format = config["title_format"]
        except KeyError:
            title_format = "{temperature}"
    if not text_format:
        try:
            text_format = config["text_format"]
        except KeyError:
            text_format = "{city}"
    if out_format is None:
        try:
            out_format = config["out_format"]
        except KeyError:
            out_format = False

    weather = Weather(api_key=api_key, location=location, units=Unit(units))
    while True:
        weather.refresh()
        weather.print(
            out_format,
            title_format=title_format,
            text_format=text_format,
        )
        if interval == 0:
            exit()
        sleep(interval)


if __name__ == "__main__":
    main()
