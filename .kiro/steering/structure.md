# Project Structure

## Directory Organization

```
.
├── main.py                 # Entry point - CLI interface and orchestration
├── config/                 # Configuration and settings
│   ├── __init__.py
│   └── settings.py        # API keys, model config, system prompt
├── services/              # External service integrations
│   ├── __init__.py
│   └── openai_service.py  # OpenAI API wrapper
├── tools/                 # Tool definitions and implementations
│   ├── __init__.py
│   ├── web_search.py      # Web search tool (OpenAI built-in)
│   ├── web_fetch.py       # Custom webpage fetching tool
│   ├── image_analysis.py  # Image analysis tool
│   └── terminal.py        # Terminal command execution tool
├── .lolo/                 # User data directory (in home)
│   └── memory.json        # Conversation history
├── docs/                  # Documentation
├── .env                   # Environment variables (not in git)
└── requirements.txt       # Python dependencies
```

## Architecture Patterns

### Service Layer Pattern
- `services/` contains wrappers for external APIs
- `OpenAIService` handles all OpenAI API interactions using Responses API
- Supports GPT-5.1 with reasoning and verbosity configuration
- Encapsulates API complexity and provides clean interface

### Tool Registration Pattern
- Tools defined as dictionaries matching OpenAI function calling schema
- Two tool types:
  - Built-in tools (e.g., `web_search`) - type: "web_search"
  - Custom functions (e.g., `fetch_webpage`, `analyze_image`, `execute_command`) - type: "function"
- All custom functions use `strict: True` for reliable schema adherence
- Tool definitions separate from implementations
- Function handlers map tool names to callable functions
- Keep tool count under 20 (currently 4 tools)

### Conversation Loop Pattern
- Iterative processing with max iterations limit (10)
- Input list accumulates conversation history (last 10 conversations)
- Handles function calls, web search, and message responses
- Continues until final message received or max iterations reached
- Tracks tool call count (max 20) and cost (warn $0.50, abort $2.00)
- Persistent memory stored in `~/.lolo/memory.json`

## Code Conventions

- **Docstrings**: Google-style docstrings for all functions and classes
- **Type hints**: Use typing module for function signatures
- **Imports**: Absolute imports from project root
- **Error handling**: Try-except blocks with user-friendly error messages
- **Rich output**: Use Rich library for terminal formatting (replaced ANSI colors)
- **Package exports**: Use `__all__` in `__init__.py` files

## Python Environment

- **Package Manager**: UV (NEVER use pip directly)
- **Virtual Environment**: `.venv` (ALWAYS activated)
- **Installation**: `uv pip install -r requirements.txt`
- **Running**: `python main.py` (within activated venv) or `uv run main.py`

## API Documentation Reference

**CRITICAL**: Always refer to `docs/` folder for correct OpenAI API syntax:

- `docs/GPT_51.md` - GPT-5.1, Responses API, reasoning, verbosity
- `docs/Function_calling.md` - Function tools, strict mode, parameters
- `docs/web_search.md` - Web search tool, citations
- `docs/image_usage.md` - Image analysis, formats, tokens

## Current Tools

1. **web_search** (built-in) - OpenAI web search with citations
   - See `docs/web_search.md` for syntax
2. **fetch_webpage** (custom) - Fetch and parse web content with bot protection bypass
   - 25,000 char limit, handles Cloudflare, cookies
   - See `docs/Function_calling.md` for function tool syntax
3. **analyze_image** (custom) - Analyze images from files or URLs
   - Supports PNG, JPEG, WEBP, GIF (max 50MB)
   - See `docs/image_usage.md` for image input formats
4. **execute_command** (custom) - Execute any zsh command with safety checks
   - Handles all file operations via standard commands (cat, ls, sed, grep, etc.)
   - Risk classification for dangerous commands (rm -rf, dd, etc.)
   - User confirmation required for risky operations
   - Non-interactive only (--noconfirm flags, no vim/nano/less)
   - Output truncated at 10,000 chars
   - Timeout: 30s default, 300s max
   - See `docs/Function_calling.md` for function tool syntax

## Adding New Tools

1. **Reference `docs/Function_calling.md`** for correct syntax
2. Create tool definition dictionary in `tools/` with `strict: True`
3. Implement handler function if custom (not built-in)
4. Export from `tools/__init__.py`
5. Add to `tools` list in `main.py`
6. Add handler to `function_handlers` dict if custom function
7. Keep total tool count under 20 for optimal performance

## Tool Design Philosophy

- **Minimize tool count**: Leverage existing capabilities (e.g., use execute_command for file ops instead of separate tools)
- **Clear descriptions**: Help model understand when and how to use each tool
- **Strict mode**: Always enable for custom functions to ensure reliable outputs
- **Safety first**: Implement risk assessment for potentially dangerous operations
- **Non-interactive only**: Commands must not require user input during execution
  - Use `--noconfirm`, `-y`, `--yes` flags
  - Use `sed`/`echo` instead of `vim`/`nano`
  - Use `cat`/`head`/`tail` instead of `less`/`more`
- **Safety limits**: Max 20 tool calls per request, max 10 iterations
- **Cost control**: Warn at $0.50, abort at $2.00 per request
- **System context**: Always include current date/time, working directory, system specs
