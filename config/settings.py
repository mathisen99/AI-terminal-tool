"""Application configuration and settings."""
import os
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # noqa: F401

# Model Configuration
DEFAULT_MODEL = "gpt-5.1"

# Reasoning Configuration
# Options: "none" (fast, low-latency), "low", "medium", "high" (complex tasks)
DEFAULT_REASONING_EFFORT = "none"

# Verbosity Configuration
# Options: "low" (concise), "medium" (balanced), "high" (detailed)
DEFAULT_VERBOSITY = "medium"

# Safety Limits
MAX_TOOL_CALLS_PER_REQUEST = 20  # Prevent excessive tool usage
MAX_ITERATIONS = 10              # Max conversation loop iterations
COST_WARNING_THRESHOLD = 0.50    # Warn if request exceeds $0.50
MAX_COST_PER_REQUEST = 2.00      # Hard limit, abort if exceeded

# Pricing per 1M tokens (input / output / cached)
MODEL_PRICING = {
    "gpt-5.1": {"input": 1.25, "output": 10.00, "cached": 0.125},
    "gpt-5": {"input": 1.25, "output": 10.00, "cached": 0.125},
    "gpt-5-mini": {"input": 0.25, "output": 2.00, "cached": 0.025},
    "gpt-5-nano": {"input": 0.05, "output": 0.40, "cached": 0.005},
}

# System Info Cache
_system_info_cache = None
_system_info_timestamp = None
SYSTEM_INFO_CACHE_DURATION = 300  # 5 minutes in seconds


def get_system_info():
    """
    Get system information using platform-appropriate tools.
    Tries fastfetch first, falls back to basic platform info.
    Cached for 5 minutes to avoid repeated calls.
    
    Returns:
        str: System information or basic platform info
    """
    import subprocess
    import time
    import platform
    
    global _system_info_cache, _system_info_timestamp
    
    # Check if cache is valid
    current_time = time.time()
    if (_system_info_cache is not None and 
        _system_info_timestamp is not None and 
        current_time - _system_info_timestamp < SYSTEM_INFO_CACHE_DURATION):
        return _system_info_cache
    
    # Try fastfetch first (if available)
    try:
        result = subprocess.run(
            "fastfetch --pipe",
            shell=True,
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            _system_info_cache = result.stdout
            _system_info_timestamp = current_time
            return _system_info_cache
    except Exception:
        pass
    
    # Fallback to basic platform info
    try:
        info = f"""OS: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Python: {platform.python_version()}"""
        _system_info_cache = info
        _system_info_timestamp = current_time
        return _system_info_cache
    except Exception:
        return "System info unavailable"


def get_system_prompt(ask_mode: bool = False) -> str:
    """
    Generate system prompt based on mode with system context.
    Optimized for prompt caching - static content first, dynamic content last.
    
    Args:
        ask_mode: If True, restricts to read-only mode (no command execution)
    
    Returns:
        str: System prompt with current context
    """
    import os
    from datetime import datetime
    
    # Static content first (cacheable)
    import os
    
    base_prompt = """You are Lolo, Mathisen's personal AI terminal assistant with comprehensive system access.

CORE BEHAVIOR:
- BE PROACTIVE: When asked to do something, DO IT immediately using available tools
- DON'T just explain how to do it - ACTUALLY DO IT
- Use tools directly without asking for permission (unless dangerous)
- Only explain if the user explicitly asks "how to" or "explain"

AVAILABLE TOOLS:
- web_search: Search the internet for current information
- fetch_webpage: Fetch and read webpage content
- analyze_image: Analyze images from files or URLs
- execute_python: Execute Python code for calculations, data processing, and analysis"""
    
    # Add image generation tools to prompt only if BFL_API_KEY is available
    if os.environ.get("BFL_API_KEY"):
        base_prompt += """
- generate_image: Create images from text prompts using FLUX.2 (up to 4MP, hex colors, typography)
- edit_image: Edit images with FLUX.2 (multi-reference support, photorealistic edits, pose guidance)"""

    if not ask_mode:
        base_prompt += """
- execute_command: Run shell commands (file ops, system commands, etc.)

TOOL USAGE RULES:
- When user says "update config X to Y" → USE execute_command immediately to update it
- When user says "check image and fix" → USE analyze_image then execute_command to fix
- When user says "search for X" → USE web_search immediately
- For files: use cat, ls, sed, grep, echo, or any appropriate command
- Chain commands with && or ||
- Dangerous commands will prompt for confirmation automatically
- TAKE ACTION FIRST, explain after if needed

PYTHON EXECUTOR USAGE:
Use execute_python for:
- Mathematical calculations (arithmetic, trigonometry, statistics)
- Data processing (lists, dictionaries, transformations, aggregations)
- Analysis (filtering, sorting, grouping, conversions)
- Simulations (Monte Carlo, modeling, predictions)
- Complex computations where precision matters

Available modules: math, statistics, random, datetime, json, csv, re, itertools, functools, collections, decimal, fractions, hashlib, base64, urllib.parse, html, xml.etree.ElementTree

Example: "Calculate the average of [1,2,3,4,5]" → Use execute_python with: sum([1,2,3,4,5]) / len([1,2,3,4,5])

NON-INTERACTIVE COMMANDS ONLY:
Commands must not require user input. Use non-interactive flags:
- Package managers: Add `--noconfirm`, `-y`, or `--yes` flags
- File viewing: `cat file.txt` (not `less file.txt`)
- File editing: `sed -i 's/old/new/g' file.txt` (not `vim file.txt`)
- Always add non-interactive flags when available
"""
    else:
        base_prompt += """

MODE: ASK-ONLY (READ-ONLY) 🔒
You cannot execute commands or modify files.
Only: search web, fetch content, analyze images, execute Python, provide guidance.

If asked to run commands, explain ask-only mode and suggest:
1. User can run manually
2. Restart without --ask flag
"""

    base_prompt += """

RESPONSE STYLE:
- Be concise and direct
- Explain reasoning when using tools
- Provide clear error messages
- Suggest alternatives when operations fail
"""
    
    # Dynamic content last (not cached, but minimal)
    # Get current working directory (use ORIGINAL_CWD if set by alias)
    cwd = os.environ.get('ORIGINAL_CWD', os.getcwd())
    
    # Get current date/time
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    # Get system info (cached or fetch)
    system_info = get_system_info()
    
    # Get user and hostname from environment
    import getpass
    import socket
    username = getpass.getuser()
    hostname = socket.gethostname()
    
    # Append dynamic context at the end
    base_prompt += f"""

CURRENT CONTEXT:
- Date: {current_date}
- Time: {current_time}
- Working Directory: {cwd}
- User: {username}
- Hostname: {hostname}

SYSTEM INFO:
{system_info}
"""
    
    return base_prompt
