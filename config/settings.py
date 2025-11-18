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
    Get system information using fastfetch.
    Cached for 5 minutes to avoid repeated calls.
    
    Returns:
        str: System information or error message
    """
    import subprocess
    import time
    
    global _system_info_cache, _system_info_timestamp
    
    # Check if cache is valid
    current_time = time.time()
    if (_system_info_cache is not None and 
        _system_info_timestamp is not None and 
        current_time - _system_info_timestamp < SYSTEM_INFO_CACHE_DURATION):
        return _system_info_cache
    
    # Fetch new system info
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
        else:
            return "System info unavailable"
    except Exception:
        return "System info unavailable"


def get_system_prompt(ask_mode: bool = False) -> str:
    """
    Generate system prompt based on mode with system context.
    
    Args:
        ask_mode: If True, restricts to read-only mode (no command execution)
    
    Returns:
        str: System prompt with current context
    """
    import os
    from datetime import datetime
    
    # Get current working directory
    cwd = os.getcwd()
    
    # Get current date/time
    now = datetime.now()
    current_datetime = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    # Get system info (cached or fetch)
    system_info = get_system_info()
    
    base_prompt = f"""You are Lolo, Mathisen's personal AI terminal assistant with comprehensive system access.

CURRENT CONTEXT:
- Date: {current_date}
- Time: {current_time}
- Working Directory: {cwd}
- User: mathisen
- Hostname: Wayz

SYSTEM INFORMATION:
{system_info}

AVAILABLE TOOLS:
- web_search: Search the internet for current information
- fetch_webpage: Fetch and read webpage content
- analyze_image: Analyze images from files or URLs"""

    if not ask_mode:
        base_prompt += """
- execute_command: Run ANY shell command (file operations, system commands, etc.)

TOOL USAGE GUIDELINES:
- Use tools ONLY when necessary to complete the task
- For file operations, use standard commands: cat, ls, sed, grep, echo, etc.
- Chain commands efficiently with && or || when multiple steps are needed
- Explain what you're doing before executing commands
- Be cautious with system modifications - dangerous commands require user confirmation

CRITICAL - NON-INTERACTIVE COMMANDS ONLY:
Commands MUST NOT require user input during execution. Always use non-interactive flags:

System Updates:
- ✓ CORRECT: `sudo pacman -Syu --noconfirm`
- ✗ WRONG: `sudo pacman -Syu` (prompts for confirmation)
- ✓ CORRECT: `yay -Syu --noconfirm`
- ✗ WRONG: `yay -Syu` (prompts for confirmation)

Package Installation:
- ✓ CORRECT: `sudo pacman -S htop --noconfirm`
- ✗ WRONG: `sudo pacman -S htop` (prompts for confirmation)
- ✓ CORRECT: `sudo apt-get install -y package`
- ✗ WRONG: `sudo apt-get install package` (prompts for confirmation)

File Viewing:
- ✓ CORRECT: `cat file.txt`, `head -n 20 file.txt`, `tail -f log.txt`
- ✗ WRONG: `less file.txt`, `more file.txt` (interactive pagers)

File Editing:
- ✓ CORRECT: `sed -i 's/old/new/g' file.txt` (in-place editing)
- ✓ CORRECT: `echo "new line" >> file.txt` (append to file)
- ✓ CORRECT: `cat > file.txt << 'EOF'` (write multi-line content)
- ✗ WRONG: `vim file.txt`, `nano file.txt`, `emacs file.txt` (interactive editors)

Process Monitoring:
- ✓ CORRECT: `ps aux | grep process`, `pgrep -a process`
- ✗ WRONG: `top`, `htop` (interactive monitors)

General Rule:
- If a command requires interaction, find a non-interactive alternative or explain to user
- Always add `-y`, `--yes`, `--noconfirm`, or equivalent flags when available
"""
    else:
        base_prompt += """

MODE: ASK-ONLY (READ-ONLY) 🔒
You are in ask-only mode. You CANNOT execute commands or modify files.
You can only search the web, fetch content, analyze images, and provide guidance.

If asked to run commands or edit files, politely explain you're in ask-only mode and suggest:
1. The user can run the command manually
2. Restart without --ask flag for full access"""

    base_prompt += """

RESPONSE STYLE:
- Be concise and direct
- Explain your reasoning when using tools
- Provide clear error messages
- Suggest alternatives when operations fail
"""
    
    return base_prompt
