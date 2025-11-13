"""Horoscope tool definition and implementation."""

# Tool definition for OpenAI function calling
horoscope_tool_definition = {
    "type": "function",
    "name": "get_horoscope",
    "description": "Get today's horoscope for an astrological sign.",
    "parameters": {
        "type": "object",
        "properties": {
            "sign": {
                "type": "string",
                "description": "An astrological sign like Taurus or Aquarius",
            },
        },
        "required": ["sign"],
    },
}


def get_horoscope(sign: str) -> str:
    """
    Get horoscope for a given astrological sign.
    
    Args:
        sign: The astrological sign (e.g., "Aquarius", "Taurus")
    
    Returns:
        A horoscope message for the sign
    """
    return f"{sign}: Next Tuesday you will befriend a baby otter."
