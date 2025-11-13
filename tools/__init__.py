"""Tools package for function calling."""
from .horoscope import get_horoscope, horoscope_tool_definition
from .weather import get_weather, weather_tool_definition
from .web_search import web_search_tool_definition
from .web_fetch import fetch_webpage, web_fetch_tool_definition

__all__ = [
    "get_horoscope",
    "horoscope_tool_definition",
    "get_weather",
    "weather_tool_definition",
    "web_search_tool_definition",
    "fetch_webpage",
    "web_fetch_tool_definition",
]
