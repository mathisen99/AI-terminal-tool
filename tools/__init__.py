"""Tools package for function calling."""
from .web_search import web_search_tool_definition
from .web_search_function import web_search, web_search_function_tool_definition
from .web_fetch import fetch_webpage, web_fetch_tool_definition
from .image_analysis import analyze_image, analyze_image_tool_definition
from .image_generation import (
    generate_image,
    generate_image_tool_definition,
    edit_image,
    edit_image_tool_definition
)
from .terminal import execute_command, execute_command_tool_definition
from .python_executor import execute_python, python_executor_tool_definition

__all__ = [
    "web_search_tool_definition",
    "web_search",
    "web_search_function_tool_definition",
    "fetch_webpage",
    "web_fetch_tool_definition",
    "analyze_image",
    "analyze_image_tool_definition",
    "generate_image",
    "generate_image_tool_definition",
    "edit_image",
    "edit_image_tool_definition",
    "execute_command",
    "execute_command_tool_definition",
    "execute_python",
    "python_executor_tool_definition",
]
