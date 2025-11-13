"""Weather tool definition and implementation."""

# Tool definition for OpenAI function calling
weather_tool_definition = {
    "type": "function",
    "name": "get_weather",
    "description": "Get current weather information for a specific location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or location (e.g., 'Paris', 'New York')",
            },
        },
        "required": ["location"],
    },
}


def get_weather(location: str) -> str:
    """
    Get weather information for a given location.
    
    Args:
        location: The location to get weather for
    
    Returns:
        Weather information as a string
    """
    # Simulated weather data
    weather_data = {
        "Paris": "Sunny, 22°C",
        "New York": "Cloudy, 18°C",
        "London": "Rainy, 15°C",
        "Tokyo": "Clear, 25°C",
        "Sydney": "Partly cloudy, 20°C",
    }
    
    # Return weather or default message
    weather = weather_data.get(location, f"Weather data not available for {location}. Assuming pleasant conditions, 20°C.")
    return f"Current weather in {location}: {weather}"
