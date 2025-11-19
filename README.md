# Lolo - AI Terminal Assistant

A powerful command-line AI assistant powered by GPT-5.1 with comprehensive tool-calling capabilities. Lolo can search the web, fetch webpages, analyze images, and execute terminal commands with intelligent safety checks.

## ✨ Features

### 🤖 GPT-5.1 Powered
- Latest OpenAI GPT-5.1 model with configurable reasoning and verbosity
- Intelligent context awareness (current date/time, working directory, system specs)
- Persistent conversation memory (stores last 50 conversations)
- Automatic prompt caching for 80% cost reduction on repeated requests
- Cost tracking and safety limits ($0.50 warning, $2.00 abort)

### 🌐 Web Capabilities
- **Web Search**: Built-in OpenAI web search with inline citations and sources
- **Web Fetch**: Advanced webpage fetching with bot protection bypass
  - Handles JavaScript-rendered pages with Selenium
  - Bypasses Cloudflare challenges with undetected-chromedriver
  - Auto-accepts cookie dialogs
  - Retry logic with exponential backoff
  - 1-hour caching for repeated fetches (99.6% faster)
  - 25,000 character limit

### 🖼️ Image Capabilities
- **Image Analysis** - Analyze images from file paths or URLs
  - Supports PNG, JPEG, WEBP, non-animated GIF
  - Smart detail level selection (auto-optimizes token usage)
  - Configurable detail levels (low: 85 tokens, high: detailed, auto: intelligent)
  - Maximum 50MB per image, up to 500 images per request
- **Image Generation** - Create images from text prompts using FLUX.1 Kontext (optional, requires BFL_API_KEY)
  - High-quality image generation with natural language prompts
  - Adjustable aspect ratios (3:7 to 7:3, default 1:1)
  - Reproducible results with seed parameter
  - JPEG or PNG output formats
  - Auto-downloads to current directory with descriptive filenames
- **Image Editing** - Edit existing images with text prompts (optional, requires BFL_API_KEY)
  - Object modifications (colors, styles, elements)
  - Text editing in images with quotation marks
  - Iterative editing with character consistency
  - Annotation box support for targeted edits
  - Works with file paths or URLs
  - Auto-saves edited images with descriptive filenames

### 💻 Terminal Command Execution
- Execute any zsh/oh-my-zsh command from anywhere on your system
- **Command visibility**: Shows command in tool call box before execution
- **Execution summary**: Lists all executed commands at the end
- Intelligent risk classification for dangerous commands
- User confirmation prompts for risky operations (rm -rf, dd, chmod -R 777, etc.)
- Command chaining support (&&, ||, pipes)
- Non-interactive only (automatic --noconfirm flags)
- File editing with sed/echo (no vim/nano)
- File viewing with cat/head/tail (no less/more)
- Output truncation (10,000 chars max)
- Configurable timeouts (30s default, 300s max)
- Command logging to ~/.lolo/command_log.txt

### 🎨 Rich Terminal Output
- Beautiful colored output with Rich library
- Animated spinners for long operations (optimized 8 fps)
- Progress indicators and live updates
- Formatted tables for usage statistics
- Panels for different message types
- Success/failure indicators with emojis
- Markdown rendering for responses
- Citation panels for web search sources

### 💾 Conversation Memory
- Persistent conversation history across sessions
- Stores last 50 conversations in ~/.lolo/memory.json
- Each conversation includes:
  - Question and response
  - Tools used
  - Token counts (input, output, cached, reasoning)
  - Cost and model information
  - Timestamp and mode
- Default mode: Continue previous conversation
- `--new` flag: Start fresh session (clears memory)
- `--ask` flag: Read-only mode (no system modifications)
- Last 10 conversations used for context

### 🔒 Safety Features
- **API key validation**: Checks for required OPENAI_API_KEY at startup
- **Conditional tool loading**: Only loads image tools if BFL_API_KEY is present
- Maximum 20 tool calls per request
- Maximum 10 iterations per conversation
- Cost warning at $0.50, abort at $2.00 per request
- Dangerous command detection and confirmation
- Interactive command prevention
- Command execution logging with timestamps
- Command visibility and execution summary
- Sudo support (NOPASSWD configured)
- Environment variable inheritance
- Working directory context preservation

### ⚡ Performance Optimizations
- Prompt caching: 80% cost reduction on cached tokens
- Tool descriptions: 40% token reduction
- Image tokens: 50% average reduction with smart detail selection
- Web fetch caching: 99.6% faster on cache hits (1 hour TTL)
- System info caching: 5 minute TTL
- Rich rendering: 40% less CPU usage with optimized spinners

## 📦 Installation

### Prerequisites

- Python 3.x
- UV package manager
- Chrome/Chromium browser (for JavaScript-rendered pages)
- **OpenAI API key** (required)
- **BFL API key** (optional - for image generation/editing)
- Arch Linux (or adapt for your system)

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
git clone https://github.com/mathisen99/AI-terminal-tool.git
cd AI-terminal-tool
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Check for UV installation
- Create a virtual environment (.venv)
- Install all dependencies
- Provide setup instructions

3. Create `.env` file and add your API keys:
```bash
# Required: OpenAI API key
echo "OPENAI_API_KEY=your_openai_key_here" > .env

# Optional: BFL API key for image generation/editing
echo "BFL_API_KEY=your_bfl_key_here" >> .env
```

**API Keys:**
- **OpenAI**: Required for all features. Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **BFL**: Optional for image generation/editing. Get from [Black Forest Labs](https://api.bfl.ai/)

If BFL_API_KEY is not set, the assistant will work normally but without image generation/editing tools.

4. (Optional) Add alias to your `.zshrc` for system-wide access:
```bash
# Add this function to ~/.zshrc
ai() {
    local original_dir="$PWD"
    (cd /path/to/AI-terminal-tool && source .venv/bin/activate && ORIGINAL_CWD="$original_dir" python main.py "$@")
}

# Replace /path/to/AI-terminal-tool with your actual path
# Then reload: source ~/.zshrc
```

## 🚀 Usage

### Basic Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Ask a question (continues previous conversation)
python main.py "What's the weather in Paris?"

# Or use uv run (auto-activates venv)
uv run main.py "What's the weather in Paris?"

# If you added the alias
ai "What's the weather in Paris?"
```

### Command-Line Flags

```bash
# Start new session (clear memory)
python main.py --new "Tell me about Python"
ai --new "Tell me about Python"

# Ask-only mode (no system modifications)
python main.py --ask "How do I use sed?"
ai --ask "How do I use sed?"
```

### Example Use Cases

```bash
# System management
ai "Check the health of my system"
ai "Update my system"
ai "How much disk space do I have left?"
ai "What's my system uptime?"

# File operations
ai "Create a file called test.txt with 'Hello World'"
ai "List all images in my home folder including subfolders"
ai "What's the biggest file in my home directory?"
ai "Find all Python files and count them"

# File editing (non-interactive)
ai "In test.txt, replace 'Hello' with 'Hi' using sed"
ai "Add a line 'New content' to the end of test.txt"

# Package management
ai "Is Firefox up to date?"
ai "Install htop"

# Image analysis
ai "Analyze the latest screenshot in my home folder"
ai "What's in this image: ~/Pictures/photo.jpg"

# Image generation
ai "Generate an image of a cute robot repairing a classic pickup truck"
ai "Create a 16:9 landscape image of a futuristic city at sunset"

# Image editing
ai "Edit ~/Pictures/car.jpg and change the car color to red"
ai "In this image ~/Pictures/sign.jpg, replace 'Hello' with 'Welcome'"

# Web research
ai "Search the web for the latest Python features"
ai "What's the current weather in Tokyo?"
ai "Fetch the content from https://example.com and summarize it"

# General questions
ai "What processes are using the most CPU?"
ai "Show me my git status"
ai "What's 15 multiplied by 23?"
```

### Command Execution Display

When executing commands, Lolo provides full transparency:

**During execution:**
```
╭─────────────────────── 💻 Tool Call ───────────────────────╮
│ execute_command                                            │
│ date --iso-8601=seconds                                    │
╰────────────────────────────────────────────────────────────╯
```

**After completion:**
```
Executed Commands:
  1. date --iso-8601=seconds
  2. ls -la *.py
```

This helps you:
- See exactly what commands are being run
- Learn useful command patterns
- Audit system operations
- Reproduce commands manually if needed

## ⚙️ Configuration

### Model Settings

Configure in `config/settings.py`:

```python
DEFAULT_MODEL = "gpt-5.1"
DEFAULT_REASONING_EFFORT = "none"  # none, low, medium, high
DEFAULT_VERBOSITY = "medium"       # low, medium, high
```

### Reasoning Levels
- `none`: Fast, low-latency (default) - best for simple queries
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

### Cache Settings

```python
SYSTEM_INFO_CACHE_DURATION = 300   # 5 minutes
WEB_CACHE_TTL = 3600               # 1 hour (in cache_manager.py)
```

## 🛠️ Tools

Lolo has access to 4-6 tools depending on available API keys (optimized to stay under 20 tool limit):

**Core Tools (always available):**

### 1. Web Search (Built-in)
- OpenAI's built-in web search
- Returns results with inline citations
- Displays clickable URLs in dedicated Sources panel
- Fast and accurate

### 2. Fetch Webpage (Custom)
- Fetches and extracts clean text from webpages
- Handles JavaScript-rendered pages with Selenium
- Bypasses bot protection and Cloudflare with undetected-chromedriver
- Auto-accepts cookie dialogs
- Retry logic with exponential backoff
- 1-hour caching for repeated fetches
- 25,000 character limit
- Optimized description: 104 chars

### 3. Analyze Image (Custom)
- Analyzes images from files or URLs
- Supports PNG, JPEG, WEBP, non-animated GIF
- Smart detail level selection:
  - Small images (< 512x512): auto-uses 'low' (85 tokens)
  - Large images (> 2048px): auto-uses 'low' (will be downscaled)
  - Medium images: uses 'high' for quality
- Maximum 50MB per image
- Optimized description: 92 chars

**Optional Tools (require BFL_API_KEY):**

### 4. Generate Image (Custom)
- Creates images from text prompts using FLUX.1 Kontext API
- High-quality image generation (1024x1024 default)
- Adjustable aspect ratios (3:7 to 7:3)
- Reproducible results with seed parameter
- JPEG or PNG output formats
- Auto-downloads to current directory with descriptive filenames

### 5. Edit Image (Custom)
- Edits existing images with text prompts using FLUX.1 Kontext API
- Object modifications (colors, styles, elements)
- Text editing with quotation marks: Replace '[old]' with '[new]'
- Iterative editing with character consistency
- Annotation box support for targeted edits
- Works with file paths or URLs
- Auto-saves edited images with descriptive filenames
- Matches input dimensions by default

**Core Tools (continued):**

### 6. Execute Command (Custom)
- Executes any zsh command
- Risk classification for dangerous commands
- User confirmation for risky operations
- Non-interactive only:
  - Package managers: auto-adds --noconfirm
  - File viewing: cat/head/tail (not less/more)
  - File editing: sed/echo (not vim/nano)
- Command chaining with && and ||
- Output truncation at 10,000 characters
- Configurable timeout (30s default, 300s max)
- Preserves working directory context when run via alias
- Optimized description: 224 chars

## 🔐 Safety Guidelines

### Command Execution Safety

Lolo implements multiple safety layers:

1. **Risk Classification**: Automatically detects dangerous patterns
   - `rm -rf`, `rm -fr` (recursive deletion)
   - `dd if=`, `dd of=` (disk operations)
   - `chmod -R 777` (permission changes)
   - `chown -R` (ownership changes)
   - `mkfs.*` (filesystem creation)
   - `fdisk`, `parted` (disk partitioning)
   - `:(){ :|:& };:` (fork bomb)
   - `curl | sh`, `wget | sh` (piped execution)
   - Direct disk device writes

2. **User Confirmation**: Prompts before executing risky commands
   - Shows the command and risk reason in a Rich panel
   - Suggests safer alternatives when available
   - Requires explicit approval (y/n prompt)
   - Logs confirmation status

3. **Interactive Command Prevention**: Blocks commands requiring user input
   - Text editors (vim, nano, emacs) → Use sed/echo instead
   - Pagers (less, more) → Use cat/head/tail instead
   - Package managers without flags → Automatically adds --noconfirm
   - Interactive monitors (top, htop) → Use ps aux instead
   - Manual pages (man) → Suggests online docs

4. **Command Logging**: All commands logged to `~/.lolo/command_log.txt`
   - Timestamp and working directory
   - Exit code and duration
   - Confirmation status for risky commands
   - Full command text

### Cost Control

- Warning displayed at $0.50 per request (yellow panel)
- Request aborted at $2.00 per request (red panel with error)
- Tool call limit: 20 per request (prevents excessive API usage)
- Iteration limit: 10 per conversation (prevents infinite loops)
- Real-time cost tracking displayed during execution

## 💾 Memory System

Conversation history is stored in `~/.lolo/memory.json`:

- Stores last 50 conversations (auto-cleanup of older ones)
- Each conversation includes:
  - Timestamp
  - Question and response
  - Tools used
  - Token counts (input, output, cached, reasoning)
  - Cost and model information
  - Reasoning effort and mode (normal/ask-only)

### Memory Management

```bash
# Continue previous conversation (default)
ai "Follow-up question"

# Start new session (clear memory)
ai --new "New topic"

# View memory location
ls -la ~/.lolo/

# View memory contents
cat ~/.lolo/memory.json

# Clear memory manually
rm ~/.lolo/memory.json
```

### Context Window

- Last 10 conversations used for context
- Enables natural follow-up questions
- Remembers both user questions and assistant responses
- Maintains conversation flow across sessions

## 🔒 Ask-Only Mode

Use `--ask` flag for read-only mode:

```bash
ai --ask "How do I configure nginx?"
```

In ask-only mode:
- ✅ Web search allowed
- ✅ Fetch webpage allowed
- ✅ Analyze image allowed
- ✅ Generate image allowed
- ✅ Edit image allowed
- ❌ Execute command blocked
- 🔒 Clear indicator in session info and question

Perfect for:
- Learning and research
- Getting guidance without system changes
- Safe exploration of commands
- Reviewing command syntax before execution

## 💰 Pricing

GPT-5.1 pricing (per 1M tokens):
- Input: $1.25
- Output: $10.00
- Cached: $0.125 (90% discount!)
- Reasoning: Counted as output tokens

Typical costs per request:
- Simple question: $0.001 - $0.01
- Web search + response: $0.01 - $0.05
- Image analysis: $0.01 - $0.10 (depends on detail level)
- Command execution: $0.005 - $0.02
- Cached request: 80% less than first request

Cost optimizations:
- Prompt caching reduces costs by 80% on repeated requests
- Optimized tool descriptions save 40% on tool definition tokens
- Smart image detail selection saves 50% on average
- Web fetch caching eliminates repeated fetch costs

## 🖥️ System Context

Lolo is aware of your system:
- **Current date and time**: Updated for each request
- **Current working directory**: Preserved when using alias
- **System specifications**: CPU, RAM, disks, GPU
- **User and hostname**: mathisen@Wayz
- **Operating system**: Arch Linux x86_64
- **Shell**: zsh with oh-my-zsh

System info is gathered via `fastfetch` and cached for 5 minutes.

## 🚀 Startup Behavior

### API Key Validation

On startup, Lolo validates your API keys:

**Required: OPENAI_API_KEY**
- If missing, shows error message with setup instructions
- Program exits immediately
- Get your key from: https://platform.openai.com/api-keys

**Optional: BFL_API_KEY**
- If missing, shows informational tip about image generation features
- Program continues normally without image generation/editing tools
- Get your key from: https://api.bfl.ai/

Example startup with BFL_API_KEY missing:
```
╭─────────────────────────── ℹ️  Optional Feature ───────────────────────────╮
│                                                                            │
│  💡 Tip: Add BFL_API_KEY to enable image generation/editing features.      │
│                                                                            │
│  Get your API key from: https://api.bfl.ai/                                │
│  Then add to .env: echo 'BFL_API_KEY=your-key-here' >> .env                │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯
```

This is informational only - the assistant works perfectly without it.

## 🐛 Troubleshooting

### UV not found
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal or reload shell config
source ~/.zshrc
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
sudo apt install chromium-browser  # Ubuntu/Debian
brew install chromium  # macOS
```

### API key errors
```bash
# Check .env file exists
ls -la .env

# View contents (be careful not to expose keys)
cat .env

# Ensure format is correct
echo "OPENAI_API_KEY=sk-..." > .env
echo "BFL_API_KEY=your_bfl_key" >> .env  # Optional
```

**Note**: If you see a message about BFL_API_KEY at startup, it's just informational. The assistant will work fine without it, just without image generation/editing features.

### Memory issues
```bash
# Clear conversation memory
ai --new "Start fresh"

# Or manually delete
rm ~/.lolo/memory.json

# View memory stats
cat ~/.lolo/memory.json | python -m json.tool
```

### Alias not working
```bash
# Check if function is defined
type ai

# Reload shell config
source ~/.zshrc

# Verify path in function is correct
which python  # Should show venv python when activated
```

### Wrong directory reported
Make sure your alias includes `ORIGINAL_CWD`:
```bash
ai() {
    local original_dir="$PWD"
    (cd /path/to/AI-terminal-tool && source .venv/bin/activate && ORIGINAL_CWD="$original_dir" python main.py "$@")
}
```

## 📁 Project Structure

```
.
├── main.py                      # Entry point and CLI interface
├── config/
│   ├── __init__.py
│   └── settings.py             # Configuration and system prompt
├── services/
│   ├── __init__.py
│   ├── openai_service.py       # OpenAI API wrapper (Responses API)
│   ├── memory_manager.py       # Conversation memory management
│   └── cache_manager.py        # Caching system for web fetches
├── tools/
│   ├── __init__.py
│   ├── web_search.py           # Web search tool definition
│   ├── web_fetch.py            # Webpage fetching tool
│   ├── image_analysis.py       # Image analysis tool
│   ├── image_generation.py     # Image generation and editing tools
│   └── terminal.py             # Command execution tool
├── utils/
│   ├── __init__.py
│   └── performance.py          # Performance monitoring utilities
├── docs/
│   ├── GPT_51.md               # GPT-5.1 API documentation
│   ├── Function_calling.md     # Function calling documentation
│   ├── web_search.md           # Web search documentation
│   ├── image_usage.md          # Image analysis documentation
│   └── PERFORMANCE_OPTIMIZATION.md  # Optimization guide
├── .env                        # Environment variables (not in git)
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── setup.sh                    # Setup script
└── README.md                   # This file
```

## 🔧 Development

### Adding New Tools

1. Create tool definition in `tools/`
2. Implement handler function
3. Export from `tools/__init__.py`
4. Add to `get_available_tools()` in `main.py`
5. Add handler to `function_handlers` dict
6. Use `strict: True` for reliable schema adherence
7. Keep tool descriptions concise (< 250 chars)

Keep total tool count under 20 for optimal performance.

### Dependencies

```
openai>=1.0.0                    # OpenAI API client
python-dotenv>=1.0.0             # Environment variable management
requests>=2.31.0                 # HTTP requests
beautifulsoup4>=4.12.0           # HTML parsing
selenium>=4.15.0                 # Browser automation
undetected-chromedriver>=3.5.0   # Bot protection bypass
Pillow>=10.0.0                   # Image processing
rich>=13.0.0                     # Terminal formatting
```

### Performance Monitoring

```python
from utils import perf_monitor

# Measure operation
with perf_monitor.measure("operation_name"):
    # Your code here
    pass

# Print performance report
perf_monitor.print_report()
```

## 📚 Documentation

- **`docs/GPT_51.md`**: GPT-5.1 model configuration and Responses API
- **`docs/Function_calling.md`**: Function tool definitions and best practices
- **`docs/web_search.md`**: Web search tool syntax and citations
- **`docs/image_usage.md`**: Image analysis formats and token calculation
- **`docs/create_images.md`**: Image generation with FLUX.1 Kontext
- **`docs/edit_images.md`**: Image editing with FLUX.1 Kontext
- **`docs/PERFORMANCE_OPTIMIZATION.md`**: Comprehensive optimization guide

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is open source. Please add your preferred license.

## 🙏 Acknowledgments

- **OpenAI** for GPT-5.1 and the Responses API
- **Rich** library for beautiful terminal output
- **UV** for fast Python package management
- **undetected-chromedriver** for bot protection bypass
- **Selenium** for browser automation
- **BeautifulSoup** for HTML parsing

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/mathisen99/AI-terminal-tool/issues)
- Check the documentation in `docs/`
- Review the command log: `~/.lolo/command_log.txt`
- Check performance docs: `docs/PERFORMANCE_OPTIMIZATION.md`

## ⚠️ Important Notes

- This assistant has full terminal access when in normal mode
- Always review commands before confirming execution, especially for dangerous operations
- Use `--ask` mode for safe exploration without system modifications
- Cost tracking helps prevent unexpected API charges
- Memory is persistent across sessions - use `--new` to start fresh
- The alias preserves your working directory context for accurate command execution

---

**Built with ❤️ for terminal enthusiasts who want AI assistance without leaving the command line.**
