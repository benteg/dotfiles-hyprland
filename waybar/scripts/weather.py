import json
import sys
from datetime import datetime
from enum import Enum
from time import sleep

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
    """Get and process weather data from the OpenWeather api"""
    def __init__(self, api_key, location, units: Unit):
        self.api_key: str = api_key
        self.location: str = location
        self.units: Unit = units
        self.error = None

    def request(self):
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

    def get_weather(self, raw_data):
        """Get weather from API data"""
        if raw_data:
            if raw_data["cod"] == 200:
                self.city = raw_data["name"]
                self.datetime = datetime.fromtimestamp(raw_data["dt"]).strftime("%H:%M")
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

    def refresh(self):
        self.get_weather(self.request())

    def print(
        self,
        as_text: bool,
        text_format: str,
        tooltip_format: str,
    ):
        """Replace format options with data and print text and tooltip as json or normal text"""
        if self.error:
            if as_text is True:
                if self.error:
                    print(self.error, self.error_tooltip, flush=True)

            else:
                if self.error:
                    print(
                        json.dumps({"text": self.error, "tooltip": self.error_tooltip}),
                        flush=True,
                    )

                    print(self.error, self.error_tooltip, flush=True)

                else:
                    if self.error:
                        print(
                            json.dumps(
                                {"text": self.error, "tooltip": self.error_tooltip}
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
                    text_format = text_format.replace(opt, format_options[opt])
                    tooltip_format = tooltip_format.replace(opt, format_options[opt])
                except AttributeError:
                    pass
            self.text = text_format
            self.tooltip = tooltip_format

            if as_text is True:
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
    "-k",
    required=False,
    help="API key to use for the request",
)
@click.option(
    "--location",
    "-l",
    required=False,
    help="Location",
)
@click.option(
    "--units",
    "-u",
    help="Chose which units to use. standard: Kelvin, metric: Celsius, imperial: Fahrenheit",
    type=click.Choice([unit.value for unit in Unit]),
    required=False,
)
@click.option(
    "--interval",
    "-i",
    help="Refresh interval. Set to 0 to get weather and exit",
    required=False,
    type=int,
)
@click.option(
    "--as-text",
    is_flag=True,
    default=False,
    required=False,
    help="Print output as plain text",
)
@click.option(
    "--text-format",
    help="Specify format for text",
    type=str,
    required=False,
)
@click.option(
    "--tooltip-format",
    help="Specify format for tooltip",
    type=str,
    required=False,
)
@click.option(
    "--config-file",
    "-c",
    help="Path to config file",
    type=click.File("r"),
    required=False,
)
@click.option(
    "--config-file",
    "-c",
    help="Path to config file",
    type=click.File("r"),
    required=False,
)
@interrupt_decorator(lambda: print("Interrupted!\nexiting..."))
def main(
    api_key: str,
    location: str,
    units: str,
    interval: int,
    text_format: str,
    tooltip_format: str,
    config_file,
    as_text: bool,
):
    # get options from config file
    # use 'and not ...' to use flag instead of config when flag is used
    if config_file:
        config = json.load(config_file)
        if config["api_key"] and not api_key:
            api_key: str = config["api_key"]
        if config["location"] and not location:
            location: str = config["location"]
        if config["units"] and not units:
            units: str = config["units"]
        if config["interval"] and not interval:
            interval = config["interval"]
        if config["text_format"] and not text_format:
            text_format: str = config["text_format"]
        if config["tooltip_format"] and not tooltip_format:
            tooltip_format: str = config["tooltip_format"]
        if config["as_text"] and not as_text:
            as_text: bool = config["as_text"]

    # Prompt for API key if not provided
    if not api_key:
        api_key = input("API key: ")
    # Prompt for location if not provided
    if not location:
        location = input("Location: ")
    #Default fallbacks
    if not units:
        units = "metric"
    if not interval:
        interval = 0
    if not text_format:
        text_format = "{temperature}"

    weather = Weather(api_key=api_key, location=location, units=Unit(units))
    while True:
        weather.refresh()
        weather.print(as_text, text_format=text_format, tooltip_format=tooltip_format)
        if interval == 0:
            sys.exit()
        sleep(interval)


if __name__ == "__main__":
    main()
