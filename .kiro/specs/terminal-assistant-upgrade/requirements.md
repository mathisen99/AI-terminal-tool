# Terminal Assistant Upgrade - Requirements

## Overview

Upgrade the AI terminal assistant to use GPT-5.1 with enhanced capabilities including web search, web fetching, image analysis, and comprehensive system tools for Arch Linux terminal operations.

## Acceptance Criteria

### AC1: GPT-5.1 Model Integration
- System uses `gpt-5.1` as the default model
- Reasoning effort configurable (`none`, `low`, `medium`, `high`)
- Verbosity configurable (`low`, `medium`, `high`)
- Uses Responses API with proper syntax from official docs

### AC2: Web Search Tool
- Integrated OpenAI built-in `web_search` tool
- Returns results with inline citations
- Displays clickable URLs in terminal output
- Configurable reasoning effort for search depth

### AC3: Enhanced Web Fetch Tool
- Fetches web content with reasonable token limits (25,000 chars maintained)
- Bypasses bot protection and Cloudflare challenges
- Handles cookie acceptance dialogs
- Parses content correctly from JavaScript-rendered pages
- Uses both requests and Selenium fallback approach

### AC4: Image Analysis Tool
- Analyzes images provided via file path or URL
- Supports PNG, JPEG, WEBP, non-animated GIF
- Maximum 50MB total payload per request
- Up to 500 images per request
- Configurable detail level (`low`, `high`, `auto`)
- Does NOT generate images (analysis only)

### AC5: Terminal Command Execution
- Execute zsh/oh-my-zsh commands
- Chain multiple commands
- Capture and return command output
- Risk classification for dangerous commands
- User confirmation prompt for risky operations (rm -rf, dd, chmod -R, etc.)
- Support for long-running commands with proper handling
- Can use standard commands (cat, ls, sed, grep, etc.) for file operations
- **CRITICAL**: Only non-interactive commands (no user input during execution)
- Automatic use of non-interactive flags (--noconfirm, -y, --yes, etc.)
- Model instructed to avoid interactive tools (vim, nano, less, more)
- Use sed/echo for file editing, cat/head/tail for viewing

### AC6: Tool Organization
- Follow best practices: aim for fewer than 20 tools
- Combine related functionality where appropriate
- Clear, descriptive tool definitions
- Efficient token usage

### AC7: Conversation Memory
- Persistent conversation history across sessions
- Each question-answer pair stored with metadata (timestamp, tokens, cost)
- Default mode: Continue previous conversation
- `--new` flag: Start fresh session with cleared memory
- Display conversation count indicator (e.g., "Question 5/10 in memory")
- Memory stored in local file (JSON format)
- Automatic memory management (limit to last N conversations)

### AC8: Ask-Only Mode
- `--ask` flag: Read-only mode with no system modifications
- Disables `execute_command` tool in ask mode
- Only allows web_search, fetch_webpage, and analyze_image
- Clear indicator when in ask-only mode
- Prevents any file edits or command execution

### AC9: Python Environment Management
- ALWAYS use UV for package management
- ALWAYS activate and use .venv virtual environment
- NEVER install packages system-wide
- All pip operations through UV: `uv pip install`, `uv pip list`, etc.
- Virtual environment activation: `source .venv/bin/activate` or `uv run`
- All Python commands run within venv context

### AC10: Tool Call Limits and Cost Control
- Maximum tool calls per request: 20 (configurable)
- Maximum iterations in conversation loop: 10 (configurable)
- Cost warning threshold: $0.50 per request (configurable)
- Abort if limits exceeded with clear error message
- Display tool call count during execution
- Track cumulative cost per session

### AC11: System Context Awareness
- System prompt includes current date and time
- System prompt includes current working directory
- System prompt includes system information (CPU, RAM, disks, etc.)
- System info gathered via fastfetch
- System info cached and refreshed periodically
- Assistant aware of user (mathisen), hostname (Wayz), OS (Arch Linux)

### AC12: User Experience
- Rich terminal output with colors, formatting, and animations
- Progress indicators with spinners for long operations
- Clear indication of tool usage with visual feedback
- Display reasoning tokens when applicable
- Cost tracking for GPT-5.1 pricing with formatted tables
- Live updates during tool execution
- Animated spinners for web searches, command execution, etc.
- Session info display (conversation count, mode)
