# Product Overview

AI Terminal Assistant - A command-line AI assistant named "Lolo" that processes natural language queries with comprehensive tool-calling capabilities for Mathisen's Arch Linux system.

## Core Features

- Natural language question processing via command line
- **GPT-5.1** powered with configurable reasoning and verbosity
- **System context aware** - Knows current date/time, working directory, system specs (CPU, RAM, disks)
- Web search integration using OpenAI's built-in web search tool with citations
- Web page fetching and content extraction (handles JavaScript-rendered pages, bot protection, Cloudflare)
- **Image analysis** - Analyze images from files or URLs (no generation)
- **Full terminal access** - Execute any zsh/oh-my-zsh command with safety checks
- File operations via standard commands (cat, ls, sed, grep, etc.)
- **Conversation memory** - Persistent history with follow-up question support (last 10 conversations)
- **Safety limits** - Max 20 tool calls, max 10 iterations, cost limits ($0.50 warning, $2.00 abort)
- **Non-interactive only** - All commands use --noconfirm flags, no vim/nano/less
- Token usage tracking and cost calculation
- Rich terminal output with colors, tables, spinners, and animations

## API Documentation

All OpenAI API implementations reference the `docs/` folder:
- `docs/GPT_51.md` - Model configuration and Responses API
- `docs/Function_calling.md` - Tool definitions
- `docs/web_search.md` - Web search syntax
- `docs/image_usage.md` - Image analysis syntax

## Usage Pattern

```bash
# Activate venv first
source .venv/bin/activate

# Default: Continue previous conversation
python main.py "Your question here"

# Start new session (clear memory)
python main.py --new "Tell me about Python"

# Ask-only mode (no system modifications)
python main.py --ask "How do I use sed?"

# Or use uv run (auto-activates venv)
uv run main.py "Your question"
```

The assistant intelligently decides when to use tools based on the query, avoiding unnecessary tool calls when information can be answered directly. Dangerous commands require user confirmation before execution.

## Example Use Cases

The assistant can handle any natural language request. Here are some examples:

```bash
# System management
python main.py "Check the health of my system"
python main.py "Update my system"
python main.py "How much disk space do I have left?"

# File operations
python main.py "Edit my .zshrc and add alias ll='ls -la'"
python main.py "List all images in my home folder including subfolders"
python main.py "Tell me the biggest file in my home directory"

# Package management
python main.py "Is Firefox up to date?"
python main.py "Install htop"

# Image analysis
python main.py "Check the latest screenshot in my home folder and tell me why I get this error"

# Or anything else you can think of!
python main.py "What processes are using the most CPU?"
python main.py "Show me my git status in all repos under ~/projects"
```

**Note**: All commands are non-interactive. The assistant automatically uses flags like `--noconfirm` for system updates and uses `sed`/`echo` instead of interactive editors like `vim`.

## Environment

- **Package Manager**: UV (ALWAYS use `uv pip` for package operations)
- **Virtual Environment**: `.venv` (ALWAYS activated before running)
- **Memory Storage**: `~/.lolo/memory.json`

## System Context

- **User**: mathisen@Wayz
- **OS**: Arch Linux x86_64
- **Shell**: zsh with oh-my-zsh
- **Model**: GPT-5.1 (default reasoning: none, verbosity: medium)
- **Hardware**: Ryzen 9 3900X, RTX 4060 Ti, 31.25 GiB RAM
- **Sudo**: NOPASSWD configured (commands work without password prompts)
