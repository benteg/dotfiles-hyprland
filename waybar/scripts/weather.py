import json
import sys
from enum import Enum
from time import sleep
from datetime import datetime

import click
import requests

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def interrupt_decorator(handler):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                handler()
                sys.exit(0)

        return wrapper

    return decorator


class Unit(Enum):
    STANDARD = "standard"
    METRIC = "metric"
    IMPERIAL = "imperial"


class Weather:
    class Temperature:
        def __init__(self, raw_data, units: Unit):
            self.temp: float = raw_data["main"]["temp"]
            self.feel: float = raw_data["main"]["feels_like"]
            self.min: float = raw_data["main"]["temp_min"]
            self.max: float = raw_data["main"]["temp_max"]
            if units == Unit.METRIC:
                self.unit = "°C"
            elif units == Unit.IMPERIAL:
                self.unit = "°F"
            elif units == Unit.STANDARD:
                self.unit = " K"
            else:
                self.unit = ""

    class Wind:
        def __init__(self, raw_data):
            self.speed = raw_data["wind"]["speed"]
            self.direction = raw_data["wind"]["deg"]
            self.icon = [
                "↑",
                "↗",
                "→",
                "↘",
                "↓",
                "↙",
                "←",
                "↖",
            ][self.direction // 45 % 8]
            try:
                self.gust = raw_data["wind"]["gust"]
            except KeyError:
                self.gust = None
            self.unit = "m/s"

    class Weather:
        def __init__(self, raw_data):
            self.main = raw_data["weather"][0]["main"]
            self.desc = raw_data["weather"][0]["description"]
            self.humid = raw_data["main"]["humidity"]
            self.icon = {
                "Thunderstorm": "",
                "Drizzle": "",
                "Rain": "",
                "Snow": "",
                "Clear": "",
                "Clouds": "",
            }[self.main]
            self.unit = "%"

    def __init__(self, api_key, location, units: Unit):
        self.api_key: str = api_key
        self.location: str = location
        self.units: Unit = units
        self.error = None

    def request(self):
        try:
            return requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.api_key}&units={self.units.value}"
            ).json()
        except requests.exceptions.HTTPError:
            self.error = "Http Error"
        except requests.exceptions.ConnectionError:
            self.error = "Connection Error"
        except requests.exceptions.Timeout:
            self.error = "Timeout Error"
        except requests.exceptions.RequestException:
            self.error = "Error"

    def get_weather(self, raw_data):
        if raw_data:
            if raw_data["cod"] == 200:
                self.city = raw_data["name"]
                self.datetime = datetime.fromtimestamp(raw_data["dt"]).strftime("%H:%M")
                self.temperature = self.Temperature(raw_data, self.units)
                self.weather = self.Weather(raw_data)
                self.wind = self.Wind(raw_data)
            else:
                self.error = f"{raw_data['cod']}: {raw_data['message'] if raw_data['message'] else 'Something went wrong'}"

    def refresh(self):
        self.get_weather(self.request())

    def print(self, format: str):
        if self.error:
            if format == "text":
                if self.error:
                    print(self.error, flush=True)

            elif format == "json":
                if self.error:
                    print(json.dumps({"text": self.error}), flush=True)

        else:
            self.text = f"{self.weather.icon} {round(self.temperature.temp, ndigits=1)}{self.temperature.unit}"
            self.tooltip = (
                f" {self.city}\n"
                f"{self.weather.icon} {self.weather.desc.capitalize()}\n"
                f" {round(self.temperature.temp, ndigits=1)}{self.temperature.unit}({round(self.temperature.feel, ndigits=1)}{self.temperature.unit})\n"
                f" {self.wind.icon} {round(self.wind.speed)}{self.wind.unit}{f'({round(self.wind.gust)}{self.wind.unit})' if self.wind.gust else ''}\n"
                f" {round(self.weather.humid, ndigits=1)}{self.weather.unit}\n"
                f" {self.datetime}"
            )

            if format == "text":
                print(
                    self.text,
                    self.tooltip,
                    sep="\n",
                    flush=True,
                )

            elif format == "json":
                print(
                    json.dumps({"text": self.text, "tooltip": self.tooltip}),
                    flush=True,
                )


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--api-key",
    "-k",
    required=True,
    help="API key to use for the request",
)
@click.option(
    "--location",
    "-l",
    required=True,
    help="Location",
)
@click.option(
    "--units",
    "-u",
    help="Chose which units to use. standard: Kelvin, metric: Celsius, imperial: Fahrenheit",
    type=click.Choice([unit.value for unit in Unit]),
    default=Unit.METRIC.value,
    required=False,
)
@click.option("--text", "format", flag_value="text", default=True)
@click.option("--json", "format", flag_value="json")
@interrupt_decorator(lambda: print("Interrupted!\nexiting..."))
def main(api_key: str, location: str, units: str, format: str):
    weather = Weather(api_key, location, Unit(units))
    weather.refresh()
    weather.print(format)


if __name__ == "__main__":
    main()
