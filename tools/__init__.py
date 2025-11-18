"""Tools package for function calling."""
from .web_search import web_search_tool_definition
from .web_fetch import fetch_webpage, web_fetch_tool_definition

__all__ = [
    "web_search_tool_definition",
    "fetch_webpage",
    "web_fetch_tool_definition",
]
