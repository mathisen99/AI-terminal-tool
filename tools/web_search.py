"""Web search tool definition and implementation."""

# Tool definition for OpenAI web search
web_search_tool_definition = {
    "type": "web_search",
}


def get_web_search_info():
    """
    Get information about web search tool.
    
    Note: This is a built-in OpenAI tool, so there's no custom implementation.
    The actual web search is performed by OpenAI's infrastructure.
    
    Returns:
        Information about the web search tool
    """
    return "Web search is a built-in OpenAI tool that searches the internet for current information."
