# Terminal Assistant Upgrade - Design

## Architecture Overview

The upgrade maintains the existing service layer pattern while adding new tools, migrating to GPT-5.1 with the Responses API, and implementing persistent conversation memory.

## Documentation References

**CRITICAL**: Always refer to the official OpenAI documentation in the `docs/` folder for correct syntax:

- **`docs/GPT_51.md`**: GPT-5.1 model configuration, Responses API, reasoning, verbosity
- **`docs/Function_calling.md`**: Function tool definitions, strict mode, parameters, best practices
- **`docs/web_search.md`**: Web search tool syntax, citations, sources
- **`docs/image_usage.md`**: Image analysis, input formats, detail levels, token calculation

These docs contain the authoritative syntax and examples. Use them as the source of truth during implementation.

## CLI Interface

### Command Modes

```bash
# Default: Continue previous conversation
python main.py "What's the weather in Paris?"

# Start new session (clear memory)
python main.py --new "Tell me about Python"

# Ask-only mode (no system modifications)
python main.py --ask "How do I use sed?"
```

### Argument Parsing

```python
import argparse

parser = argparse.ArgumentParser(description="Lolo - AI Terminal Assistant")
parser.add_argument("question", nargs="+", help="Your question")
parser.add_argument("--new", action="store_true", help="Start new session (clear memory)")
parser.add_argument("--ask", action="store_true", help="Ask-only mode (no commands/edits)")
args = parser.parse_args()
```

## Model Configuration

### GPT-5.1 Settings
- **Default model**: `gpt-5.1`
- **Default reasoning**: `none` (for fast responses)
- **Default verbosity**: `medium`
- **Pricing** (per 1M tokens):
  - Input: $1.25
  - Output: $10.00
  - Cached: $0.125

### Reasoning Strategy
- `none`: Fast, low-latency interactions (default)
- `low`: Simple queries with minimal thinking
- `medium`: Moderate complexity tasks
- `high`: Complex coding, debugging, multi-step planning

## Safety Limits

### Tool Call Limits
```python
# config/settings.py
MAX_TOOL_CALLS_PER_REQUEST = 20  # Prevent excessive tool usage
MAX_ITERATIONS = 10              # Max conversation loop iterations
COST_WARNING_THRESHOLD = 0.50    # Warn if request exceeds $0.50
MAX_COST_PER_REQUEST = 2.00      # Hard limit, abort if exceeded
```

### Implementation
```python
def process_question(question: str):
    tool_call_count = 0
    iteration = 0
    total_cost = 0.0
    
    while iteration < MAX_ITERATIONS:
        iteration += 1
        response = service.create_response(input_list, tools)
        
        # Track cost
        total_cost += calculate_cost(response.usage, model)
        
        # Check cost limits
        if total_cost > MAX_COST_PER_REQUEST:
            console.print(f"[red]Aborted: Cost limit exceeded (${total_cost:.2f})[/red]")
            break
        elif total_cost > COST_WARNING_THRESHOLD:
            console.print(f"[yellow]Warning: High cost (${total_cost:.2f})[/yellow]")
        
        # Count tool calls
        for item in response.output:
            if item.type in ["function_call", "web_search_call"]:
                tool_call_count += 1
                
        # Check tool call limit
        if tool_call_count > MAX_TOOL_CALLS_PER_REQUEST:
            console.print(f"[red]Aborted: Too many tool calls ({tool_call_count})[/red]")
            break
        
        # Process response...
```

## Tool Design

### Tool Organization Strategy
Based on best practices research, we'll organize tools into logical groups:

1. **Web Tools** (2 tools)
   - `web_search` (built-in OpenAI tool)
   - `fetch_webpage` (custom function)

2. **Image Tools** (1 tool)
   - `analyze_image` (custom function)

3. **Terminal Tools** (1 tool)
   - `execute_command` (custom function with risk assessment)
   - Handles all file operations via standard commands (cat, ls, sed, grep, vim, etc.)

**Total: 4 tools** (well under the 20 tool recommendation)

**Rationale**: File operations don't need dedicated tools since `execute_command` can run `cat`, `ls`, `sed`, `echo >`, etc. This keeps the tool count minimal and leverages existing shell capabilities.

## Tool Definitions

**Note**: All tool definitions follow the syntax documented in `docs/Function_calling.md` and `docs/web_search.md`. Always verify against these docs.

### 1. Web Search (Built-in)

**Reference**: `docs/web_search.md`

```python
{
    "type": "web_search"
}
```

### 2. Fetch Webpage (Enhanced)

**Reference**: `docs/Function_calling.md` (function tool syntax, strict mode)

```python
{
    "type": "function",
    "name": "fetch_webpage",
    "description": "Fetch and extract clean text from a webpage. Handles JavaScript-rendered pages and bypasses bot protection. Returns up to 25,000 characters.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL to fetch (e.g., 'https://example.com')"
            }
        },
        "required": ["url"],
        "additionalProperties": False
    },
    "strict": True
}
```

**Implementation enhancements**:
- Add undetected-chromedriver for better bot protection bypass
- Implement cookie dialog auto-acceptance
- Add retry logic with exponential backoff
- Better Cloudflare challenge handling

### 3. Analyze Image

**Reference**: `docs/image_usage.md` (image input formats, detail parameter)

```python
{
    "type": "function",
    "name": "analyze_image",
    "description": "Analyze an image from a file path or URL. Supports PNG, JPEG, WEBP, GIF. Returns detailed description of image contents.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_source": {
                "type": "string",
                "description": "File path or URL to the image"
            },
            "detail": {
                "type": ["string", "null"],
                "enum": ["low", "high", "auto"],
                "description": "Level of detail for analysis. 'low' is faster, 'high' is more detailed. Default: 'auto'"
            },
            "question": {
                "type": ["string", "null"],
                "description": "Optional specific question about the image"
            }
        },
        "required": ["image_source"],
        "additionalProperties": False
    },
    "strict": True
}
```

**Implementation**:
- Use Responses API with `input_image` content type
- Support both URL and base64-encoded local files
- Validate file size (max 50MB)
- Return structured analysis results

### 4. Execute Command

**Reference**: `docs/Function_calling.md` (function tool syntax, strict mode, parameters)

```python
{
    "type": "function",
    "name": "execute_command",
    "description": "Execute a shell command in zsh. Can run any command including file operations (cat, ls, sed, grep, echo, vim, etc.). Returns stdout, stderr, and exit code. DANGEROUS commands require user confirmation.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute. Can be chained with && or ||. Examples: 'ls -la', 'cat file.txt', 'echo \"content\" > file.txt', 'sed -i \"s/old/new/g\" file.txt'"
            },
            "working_dir": {
                "type": ["string", "null"],
                "description": "Working directory for command execution. Default: current directory"
            },
            "timeout": {
                "type": ["integer", "null"],
                "description": "Timeout in seconds. Default: 30. Use higher values for long-running commands."
            }
        },
        "required": ["command"],
        "additionalProperties": False
    },
    "strict": True
}
```

**Risk Classification**:
Dangerous patterns requiring confirmation:
- `rm -rf`, `rm -fr`
- `dd if=`, `dd of=`
- `chmod -R 777`
- `chown -R`
- `mkfs.*`
- `fdisk`, `parted`
- `:(){ :|:& };:` (fork bomb)
- Commands with `sudo` modifying system files
- `curl | sh`, `wget | sh`

**Interactive Command Handling**:
Commands requiring user input MUST use non-interactive flags:
- `pacman -Syu` → `pacman -Syu --noconfirm` (Arch Linux updates)
- `yay -Syu` → `yay -Syu --noconfirm` (AUR updates)
- `sudo` commands → Use `SUDO_ASKPASS` or require password beforehand
- `vim`, `nano` → Use `sed`, `echo`, or `cat` for file editing instead
- `less`, `more` → Use `cat` or `head`/`tail` instead
- Any command with prompts → Add `-y`, `--yes`, `--noconfirm`, or equivalent flags

The model should be instructed to ALWAYS use non-interactive versions of commands.

## New Components

### Memory Manager

Create `services/memory_manager.py`:

```python
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class MemoryManager:
    """Manages conversation history and persistence."""
    
    def __init__(self, memory_path: str = "~/.lolo/memory.json", max_conversations: int = 50):
        self.memory_path = Path(memory_path).expanduser()
        self.max_conversations = max_conversations
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_memory(self) -> Dict[str, Any]:
        """Load conversation memory from file."""
        if not self.memory_path.exists():
            return {
                "conversations": [],
                "total_conversations": 0,
                "total_cost": 0.0,
                "last_updated": None
            }
        
        with open(self.memory_path, 'r') as f:
            return json.load(f)
    
    def save_memory(self, memory: Dict[str, Any]):
        """Save conversation memory to file."""
        memory["last_updated"] = datetime.now().isoformat()
        
        with open(self.memory_path, 'w') as f:
            json.dump(memory, f, indent=2)
    
    def add_conversation(self, memory: Dict[str, Any], conversation: Dict[str, Any]):
        """Add new conversation to memory."""
        memory["conversations"].append(conversation)
        memory["total_conversations"] += 1
        memory["total_cost"] += conversation.get("cost", 0.0)
        
        # Cleanup old conversations if limit exceeded
        if len(memory["conversations"]) > self.max_conversations:
            memory["conversations"] = memory["conversations"][-self.max_conversations:]
        
        self.save_memory(memory)
    
    def clear_memory(self):
        """Clear all conversation history."""
        if self.memory_path.exists():
            self.memory_path.unlink()
    
    def get_context_messages(self, memory: Dict[str, Any], limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversations for context."""
        messages = []
        for conv in memory["conversations"][-limit:]:
            messages.append({"role": "user", "content": conv["question"]})
            messages.append({"role": "assistant", "content": conv["response"]})
        return messages
```

## Service Layer Updates

### OpenAIService Enhancements

```python
class OpenAIService:
    def __init__(self, model: str = "gpt-5.1", reasoning: str = "none", verbosity: str = "medium"):
        self.client = OpenAI()
        self.model = model
        self.reasoning = reasoning
        self.verbosity = verbosity
    
    def create_response(
        self,
        input_list: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        reasoning: Dict[str, str] = None,
        text: Dict[str, str] = None,
        tool_choice: str = "auto"
    ) -> Any:
        """Create response using Responses API with GPT-5.1"""
        kwargs = {
            "model": self.model,
            "tools": tools,
            "input": input_list,
            "tool_choice": tool_choice,
        }
        
        # Add reasoning configuration
        if reasoning:
            kwargs["reasoning"] = reasoning
        else:
            kwargs["reasoning"] = {"effort": self.reasoning}
        
        # Add verbosity configuration
        if text:
            kwargs["text"] = text
        else:
            kwargs["text"] = {"verbosity": self.verbosity}
        
        return self.client.responses.create(**kwargs)
```

## System Prompt Updates

```python
def get_system_prompt(ask_mode: bool = False) -> str:
    """Generate system prompt based on mode with system context."""
    import os
    import subprocess
    from datetime import datetime
    
    # Get current working directory
    cwd = os.getcwd()
    
    # Get current date/time
    now = datetime.now()
    current_datetime = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    # Get system info (cached or fetch)
    try:
        result = subprocess.run(
            "fastfetch --pipe",
            shell=True,
            capture_output=True,
            text=True,
            timeout=2
        )
        system_info = result.stdout if result.returncode == 0 else "System info unavailable"
    except:
        system_info = "System info unavailable"
    
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
- System updates: Add `--noconfirm` flag (e.g., `sudo pacman -Syu --noconfirm`)
- Package operations: Add `--noconfirm` or `-y` flags
- File viewing: Use `cat`, `head`, `tail` (NEVER `less`, `more`)
- File editing: Use `sed`, `echo >>`, `cat >` (NEVER `vim`, `nano`, interactive editors)
- Any command with prompts: Add `-y`, `--yes`, `--noconfirm`, or equivalent flags
- If a command requires interaction, find a non-interactive alternative or explain to user"""
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
```
```

## Rich Terminal Output

### Rich Library Integration

Use Rich library for enhanced terminal UI:

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()
```

### Visual Elements

1. **Spinners**: Show during API calls, tool execution
2. **Progress bars**: For long-running operations
3. **Tables**: Display usage statistics and costs
4. **Panels**: Highlight important information (errors, confirmations)
5. **Markdown**: Format model responses with proper styling
6. **Live updates**: Real-time status during tool execution

### Output Examples

**Tool execution**:
```
🔧 Calling tool: execute_command
⠋ Running: ls -la /home/user
✓ Command completed (0.2s)
```

**Web search**:
```
🌐 Searching the web...
⠋ Query: "latest Python features"
✓ Found 5 sources
```

**Cost tracking**:
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric            ┃ Value     ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Model             │ gpt-5.1   │
│ Input tokens      │ 1,234     │
│ Output tokens     │ 567       │
│ Cached tokens     │ 890       │
│ Cost              │ $0.0123   │
└───────────────────┴───────────┘
```

## Conversation Memory

### Memory Storage

Store conversation history in `~/.lolo/memory.json`:

```json
{
  "conversations": [
    {
      "timestamp": "2025-11-18T10:30:00Z",
      "question": "What's the weather in Paris?",
      "response": "The weather in Paris is...",
      "tools_used": ["web_search"],
      "tokens": {
        "input": 1234,
        "output": 567,
        "cached": 890
      },
      "cost": 0.0123,
      "reasoning_effort": "none"
    }
  ],
  "total_conversations": 5,
  "total_cost": 0.0567,
  "last_updated": "2025-11-18T10:30:00Z"
}
```

### Memory Management

- **Max conversations**: 50 (configurable in settings)
- **Auto-cleanup**: Remove oldest when limit exceeded
- **Memory stats**: Display at start of each session
- **Clear command**: `--new` flag clears memory

### Context Building

```python
def build_input_context(memory, new_question, system_prompt):
    """Build input list from memory and new question."""
    input_list = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history from memory
    for conv in memory["conversations"][-10:]:  # Last 10 conversations
        input_list.append({
            "role": "user",
            "content": conv["question"]
        })
        input_list.append({
            "role": "assistant", 
            "content": conv["response"]
        })
    
    # Add new question
    input_list.append({
        "role": "user",
        "content": new_question
    })
    
    return input_list
```

### Memory Display

Show at start of each session:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Session Info                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Conversations in memory: 5/50              │
│ Total cost (session): $0.0567              │
│ Mode: Normal                               │
└────────────────────────────────────────────┘
```

For ask-only mode:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Session Info                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Conversations in memory: 5/50              │
│ Total cost (session): $0.0567              │
│ Mode: Ask-Only (Read-Only) 🔒             │
└────────────────────────────────────────────┘
```

## Ask-Only Mode

### Tool Restrictions

When `--ask` flag is used:

```python
def get_available_tools(ask_mode: bool):
    """Return tools based on mode."""
    tools = [
        web_search_tool_definition,
        web_fetch_tool_definition,
        analyze_image_tool_definition,
    ]
    
    # Only add execute_command in normal mode
    if not ask_mode:
        tools.append(execute_command_tool_definition)
    
    return tools
```

### System Prompt Update

Add mode information to system prompt:

```python
if ask_mode:
    SYSTEM_PROMPT += """

MODE: ASK-ONLY (READ-ONLY)
You are in ask-only mode. You CANNOT execute commands or modify files.
You can only:
- Search the web
- Fetch webpage content
- Analyze images
- Provide information and guidance

If the user asks you to run commands or edit files, politely explain you're in ask-only mode.
"""
```

## Data Flow

### Multi-turn Conversation with Tools

```
User Input + CLI Args
    ↓
[Parse Arguments: question, --new, --ask]
    ↓
[Load Memory (unless --new)]
    ↓
[Display Session Info with Rich Panel]
    ↓
[Build Input Context from Memory]
    ↓
[Get Available Tools (based on --ask mode)]
    ↓
[Show Spinner: "Processing..."]
    ↓
[GPT-5.1 Responses API]
    ↓
[Check Response Type]
    ├─→ Message → Display with Rich Markdown → Save to Memory → Done
    ├─→ Function Call → Show Spinner → Execute → Add to Input → Loop
    ├─→ Web Search → Show Progress → Loop
    └─→ Reasoning → Track Tokens → Continue
    ↓
[Update Memory File]
    ↓
[Display Updated Stats]
```

## Error Handling

### Tool Execution Errors
- File not found: Suggest `list_directory` to find correct path
- Permission denied: Explain issue and suggest `sudo` if appropriate
- Command timeout: Offer to increase timeout or run in background
- Network errors: Retry with exponential backoff (max 3 attempts)

### Image Analysis Errors
- File too large: Suggest compression or resizing
- Unsupported format: List supported formats
- Invalid URL: Validate URL format before sending

## Token Management

### Image Token Calculation
For GPT-5.1 (uses same calculation as gpt-5-mini):
- Base multiplier: 1.62
- Token cost = patches × 1.62
- Patches = ceil(width/32) × ceil(height/32)
- Max patches: 1536

### Cost Tracking
Update `MODEL_PRICING` to include GPT-5.1:
```python
MODEL_PRICING = {
    "gpt-5.1": {"input": 1.25, "output": 10.00, "cached": 0.125},
    "gpt-5": {"input": 1.25, "output": 10.00, "cached": 0.125},
    "gpt-5-mini": {"input": 0.25, "output": 2.00, "cached": 0.025},
    "gpt-5-nano": {"input": 0.05, "output": 0.40, "cached": 0.005},
}
```

## Security Considerations

### Command Execution Safety
1. **Risk Assessment**: Classify commands before execution
2. **User Confirmation**: Prompt for dangerous operations
3. **Sandboxing**: Consider running in restricted environment
4. **Logging**: Log all executed commands with timestamps
5. **Timeout Protection**: Prevent infinite loops (default 30s, max 300s)
6. **Output Truncation**: Limit output to 10,000 characters to prevent token overflow
7. **Sudo Handling**: Detect sudo commands, use `sudo -n` (non-interactive), warn if auth fails
8. **Environment Inheritance**: Pass full environment to subprocess for proper command execution
9. **Working Directory**: Execute from directory where main.py was invoked

### File System Access (via execute_command)
1. **Command Validation**: Check for dangerous patterns before execution
2. **User Confirmation**: Required for risky file operations (rm -rf, etc.)
3. **Output Truncation**: Limit command output to prevent token overflow
4. **Backup Suggestion**: Recommend backups before destructive modifications

## Python Environment Management

### UV Package Manager

**CRITICAL**: This project uses UV for all Python package operations.

```bash
# Create virtual environment
uv venv

# Activate venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Add new package
uv pip install package-name

# Run application (within venv)
python main.py "question"

# Or use uv run (auto-activates)
uv run main.py "question"
```

### Virtual Environment Rules

1. **ALWAYS** activate `.venv` before running Python
2. **NEVER** install packages system-wide
3. **ALWAYS** use `uv pip` instead of `pip`
4. **ALWAYS** run commands within venv context

### Installation Script

Create `setup.sh` for easy setup:

```bash
#!/bin/bash
# Setup script for Lolo AI Terminal Assistant

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: UV is not installed"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

echo "Setup complete! Activate venv with: source .venv/bin/activate"
```

## Performance Optimization

### Prompt Caching
- System prompt is static → eligible for caching
- Tool definitions are static → eligible for caching
- Expected cache hit rate: 60-80% after first request

### Reasoning Effort Strategy
- Start with `none` for simple queries
- Escalate to `low` or `medium` if initial response inadequate
- Use `high` only for complex debugging or multi-step tasks

### Token Efficiency
- Use `detail: "low"` for images when high detail not needed
- Limit web fetch to 25,000 chars
- Truncate command output if excessive (>10,000 chars)
