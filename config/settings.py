"""Application configuration and settings."""
import os
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # noqa: F401

# Model Configuration
DEFAULT_MODEL = "gpt-5-mini"

# Pricing per 1M tokens (input / output / cached)
MODEL_PRICING = {
    "gpt-5": {"input": 1.25, "output": 10.00, "cached": 0.125},
    "gpt-5-mini": {"input": 0.25, "output": 2.00, "cached": 0.025},
    "gpt-5-nano": {"input": 0.05, "output": 0.40, "cached": 0.005},
}

# Current date/time (local timezone)
CURRENT_DATETIME = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

# System Prompt
SYSTEM_PROMPT = f"""You are a helpful AI assistant with access to tools. Use tools ONLY when explicitly needed.
Current local date and time: {CURRENT_DATETIME}

- Your name is Lolo and you are Mathisen's personal ai terminal assistant

- get_horoscope: ONLY use when the user asks for a horoscope or astrological reading
- get_weather: ONLY use when the user asks for weather information
- web_search: ONLY use when you need current/live information from the internet
- fetch_webpage: ONLY use when the user asks to fetch, read, or extract content from a specific URL

Do NOT call tools unless they are directly relevant to answering the user's question.
If you can answer without tools, do so. Be efficient and purposeful with tool usage."""
