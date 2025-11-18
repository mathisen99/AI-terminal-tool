# Lolo - AI Terminal Assistant

A powerful command-line AI assistant powered by GPT-5.1 with comprehensive tool-calling capabilities for Arch Linux systems. Lolo can search the web, fetch webpages, analyze images, and execute terminal commands with intelligent safety checks.

## Features

### 🤖 GPT-5.1 Powered
- Latest OpenAI GPT-5.1 model with configurable reasoning and verbosity
- Intelligent context awareness (current date/time, working directory, system specs)
- Persistent conversation memory with follow-up question support
- Cost tracking and safety limits

### 🌐 Web Capabilities
- **Web Search**: Built-in OpenAI web search with inline citations
- **Web Fetch**: Advanced webpage fetching with bot protection bypass
  - Handles JavaScript-rendered pages
  - Bypasses Cloudflare challenges
  - Auto-accepts cookie dialogs
  - Retry logic with exponential backoff

### 🖼️ Image Analysis
- Analyze images from file paths or URLs
- Supports PNG, JPEG, WEBP, non-animated GIF
- Configurable detail levels (low, high, auto)
- Maximum 50MB per image

### 💻 Terminal Command Execution
- Execute any zsh/oh-my-zsh command
- Intelligent risk classification for dangerous commands
- User confirmation prompts for risky operations
- Command chaining support (&&, ||)
- Non-interactive only (automatic --noconfirm flags)
- Output truncation (10,000 chars max)
- Configurable timeouts (30s default, 300s max)

### 🎨 Rich Terminal Output
- Beautiful colored output with Rich library
- Animated spinners for long operations
- Progress indicators and live updates
- Formatted tables for usage statistics
- Panels for different message types
- Success/failure indicators with emojis

### 💾 Conversation Memory
- Persistent conversation history across sessions
- Stores last 50 conversations
- Default mode: Continue previous conversation
- `--new` flag: Start fresh session
- `--ask` flag: Read-only mode (no system modifications)

### 🔒 Safety Features
- Maximum 20 tool calls per request
- Maximum 10 iterations per conversation
- Cost warning at $0.50, abort at $2.00
- Dangerous command detection and confirmation
- Interactive command prevention
- Command execution logging

## Installation

### Prerequisites

- Python 3.x
- UV package manager
- Chrome/Chromium browser (for JavaScript-rendered pages)
- OpenAI API key

### Install UV

UV is required for package management. Install it using one of these methods:

```bash
# Official installer (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Using pip
pip install uv

# Using Homebrew (macOS/Linux)
brew install uv
```

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Ai-cli-tool
```

2. Run the setup script:
```bash
./setup.sh
```

This will:
- Check for UV installation
- Create a virtual environment (.venv)
- Install all dependencies
- Create .env file template
- Create .lolo directory for memory storage

3. Add your OpenAI API key to `.env`:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Ask a question (continues previous conversation)
python main.py "What's the weather in Paris?"

# Or use uv run (auto-activates venv)
uv run main.py "What's the weather in Paris?"
```

### Command-Line Flags

```bash
# Start new session (clear memory)
python main.py --new "Tell me about Python"

# Ask-only mode (no system modifications)
python main.py --ask "How do I use sed?"
```

### Example Use Cases

```bash
# System management
python main.py "Check the health of my system"
python main.py "Update my system"
python main.py "How much disk space do I have left?"

# File operations
python main.py "Edit my .zshrc and add alias ll='ls -la'"
python main.py "List all images in my home folder"
python main.py "What's the biggest file in my home directory?"

# Package management
python main.py "Is Firefox up to date?"
python main.py "Install htop"

# Image analysis
python main.py "Analyze the latest screenshot in my home folder"

# Web research
python main.py "What are the latest Python features?"
python main.py "Fetch the content from https://example.com"

# General questions
python main.py "What processes are using the most CPU?"
python main.py "Show me my git status in all repos under ~/projects"
```

## Configuration

### Model Settings

Configure in `config/settings.py`:

```python
DEFAULT_MODEL = "gpt-5.1"
DEFAULT_REASONING_EFFORT = "none"  # none, low, medium, high
DEFAULT_VERBOSITY = "medium"       # low, medium, high
```

### Reasoning Levels
- `none`: Fast, low-latency (default)
- `low`: Simple queries with minimal thinking
- `medium`: Moderate complexity tasks
- `high`: Complex coding, debugging, multi-step planning

### Verbosity Levels
- `low`: Concise responses
- `medium`: Balanced (default)
- `high`: Detailed explanations

### Safety Limits

```python
MAX_TOOL_CALLS_PER_REQUEST = 20   # Max tool calls per request
MAX_ITERATIONS = 10                # Max conversation loop iterations
COST_WARNING_THRESHOLD = 0.50      # Warn if request exceeds $0.50
MAX_COST_PER_REQUEST = 2.00        # Abort if request exceeds $2.00
```

## Tools

Lolo has access to 4 tools:

### 1. Web Search (Built-in)
- OpenAI's built-in web search
- Returns results with inline citations
- Displays clickable URLs

### 2. Fetch Webpage (Custom)
- Fetches and extracts clean text from webpages
- Handles JavaScript-rendered pages
- Bypasses bot protection and Cloudflare
- 25,000 character limit

### 3. Analyze Image (Custom)
- Analyzes images from files or URLs
- Supports PNG, JPEG, WEBP, non-animated GIF
- Configurable detail level
- Maximum 50MB per image

### 4. Execute Command (Custom)
- Executes any zsh command
- Risk classification for dangerous commands
- User confirmation for risky operations
- Non-interactive only (no vim, nano, less, etc.)
- Automatic --noconfirm flags for package managers
- Output truncation at 10,000 characters

## Safety Guidelines

### Command Execution Safety

Lolo implements multiple safety layers:

1. **Risk Classification**: Automatically detects dangerous patterns
   - `rm -rf`, `dd`, `chmod -R 777`, etc.
   - Fork bombs and malicious scripts
   - Direct disk device writes

2. **User Confirmation**: Prompts before executing risky commands
   - Shows the command and risk reason
   - Suggests safer alternatives
   - Requires explicit approval

3. **Interactive Command Prevention**: Blocks commands requiring user input
   - Text editors (vim, nano) → Use sed/echo instead
   - Pagers (less, more) → Use cat/head/tail instead
   - Package managers → Automatically adds --noconfirm

4. **Command Logging**: All commands logged to `~/.lolo/command_log.txt`
   - Timestamp, working directory, exit code
   - Duration and confirmation status

### Cost Control

- Warning displayed at $0.50 per request
- Request aborted at $2.00 per request
- Tool call limit: 20 per request
- Iteration limit: 10 per conversation

## Memory System

Conversation history is stored in `~/.lolo/memory.json`:

- Stores last 50 conversations
- Each conversation includes:
  - Question and response
  - Tools used
  - Token counts (input, output, cached, reasoning)
  - Cost and model information
  - Timestamp

### Memory Management

```bash
# Continue previous conversation (default)
python main.py "Follow-up question"

# Start new session (clear memory)
python main.py --new "New topic"

# View memory location
ls -la ~/.lolo/
```

## Ask-Only Mode

Use `--ask` flag for read-only mode:

```bash
python main.py --ask "How do I configure nginx?"
```

In ask-only mode:
- ✅ Web search allowed
- ✅ Fetch webpage allowed
- ✅ Analyze image allowed
- ❌ Execute command blocked

Perfect for:
- Learning and research
- Getting guidance without system changes
- Safe exploration of commands

## Pricing

GPT-5.1 pricing (per 1M tokens):
- Input: $1.25
- Output: $10.00
- Cached: $0.125

Typical costs:
- Simple question: $0.001 - $0.01
- Web search + response: $0.01 - $0.05
- Image analysis: $0.01 - $0.10
- Command execution: $0.005 - $0.02

## System Context

Lolo is aware of your system:
- Current date and time
- Current working directory
- System specifications (CPU, RAM, disks)
- User and hostname
- Operating system

System info is cached and refreshed every 5 minutes using `fastfetch`.

## Troubleshooting

### UV not found
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal
source ~/.bashrc  # or ~/.zshrc
```

### Virtual environment issues
```bash
# Remove and recreate
rm -rf .venv
./setup.sh
```

### ChromeDriver errors
```bash
# Install Chrome/Chromium
sudo pacman -S chromium  # Arch Linux
```

### API key errors
```bash
# Check .env file
cat .env

# Ensure key is set correctly
OPENAI_API_KEY=sk-...
```

### Memory issues
```bash
# Clear conversation memory
python main.py --new "Start fresh"

# Or manually delete
rm ~/.lolo/memory.json
```

## Project Structure

```
.
├── main.py                 # Entry point and CLI interface
├── config/
│   ├── __init__.py
│   └── settings.py        # Configuration and system prompt
├── services/
│   ├── __init__.py
│   ├── openai_service.py  # OpenAI API wrapper
│   └── memory_manager.py  # Conversation memory management
├── tools/
│   ├── __init__.py
│   ├── web_fetch.py       # Webpage fetching tool
│   ├── image_analysis.py  # Image analysis tool
│   └── terminal.py        # Command execution tool
├── docs/                  # API documentation
├── .env                   # Environment variables (not in git)
├── requirements.txt       # Python dependencies
└── setup.sh              # Setup script
```

## Development

### Adding New Tools

1. Create tool definition in `tools/`
2. Implement handler function
3. Export from `tools/__init__.py`
4. Add to `get_available_tools()` in `main.py`
5. Add handler to `function_handlers` dict

Keep total tool count under 20 for optimal performance.

### Running Tests

```bash
# Activate venv
source .venv/bin/activate

# Run tests (when implemented)
pytest
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- OpenAI for GPT-5.1 and API
- Rich library for beautiful terminal output
- UV for fast Python package management
- undetected-chromedriver for bot protection bypass

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the documentation in `docs/`
- Review the command log: `~/.lolo/command_log.txt`

---

**Note**: This assistant has full terminal access. Always review commands before confirming execution, especially for dangerous operations.
