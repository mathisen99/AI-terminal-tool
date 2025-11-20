# Technology Stack

## Core Technologies

- **Python 3.x** - Primary language
- **OpenAI API** - LLM provider with GPT-5.1, Responses API, function calling, and web search
- **Requests + BeautifulSoup4** - Web scraping and HTML parsing
- **Selenium + undetected-chromedriver** - JavaScript-rendered page handling with bot protection bypass
- **Pillow** - Image processing and validation
- **Rich** - Beautiful terminal output with colors, tables, progress bars, and animations
- **python-dotenv** - Environment variable management

## API Documentation

**CRITICAL**: Always refer to the `docs/` folder for correct OpenAI API syntax:

- **`docs/GPT_51.md`** - GPT-5.1 model, Responses API, reasoning, verbosity
- **`docs/Function_calling.md`** - Function tool definitions, strict mode, parameters
- **`docs/web_search.md`** - Web search tool, citations, sources
- **`docs/image_usage.md`** - Image analysis, formats, detail levels, token calculation

These docs contain the authoritative syntax and examples. Use them as the source of truth.

## Dependencies

See `requirements.txt` for exact versions:
- openai>=1.0.0
- python-dotenv>=1.0.0
- requests>=2.31.0
- beautifulsoup4>=4.12.0
- selenium>=4.15.0
- undetected-chromedriver>=3.5.0
- Pillow>=10.0.0
- rich>=13.0.0

## Environment Setup

Required environment variables in `.env`:
- `OPENAI_API_KEY` - OpenAI API key

## Python Environment Management

**CRITICAL**: This project uses UV for package management and ALWAYS runs in a virtual environment.

### Setup

```bash
# Create virtual environment (first time only)
uv venv

# Activate virtual environment
source .venv/bin/activate
```

### Package Management

```bash
# Install dependencies (ALWAYS use uv pip)
uv pip install -r requirements.txt

# Add new package
uv pip install package-name

# List installed packages
uv pip list

# Update package
uv pip install --upgrade package-name
```

**NEVER**:
- Use `pip install` directly (always use `uv pip`)
- Install packages system-wide
- Run Python commands outside the venv

## Common Commands

```bash
# Activate venv first
source .venv/bin/activate

# Run the assistant (default: continue conversation)
python main.py "Your question"

# Start new session
python main.py --new "Tell me about Python"

# Ask-only mode (no commands/edits)
python main.py --ask "How do I use sed?"

# Or use uv run directly (auto-activates venv)
uv run main.py "Your question"
```

## Model Configuration

Default model: `gpt-5.1`

Available models with pricing (per 1M tokens):
- **gpt-5.1**: $1.25 input / $10.00 output / $0.125 cached (default)
- gpt-5: $1.25 input / $10.00 output / $0.125 cached
- gpt-5-mini: $0.25 input / $2.00 output / $0.025 cached
- gpt-5-nano: $0.05 input / $0.40 output / $0.005 cached

### Reasoning Configuration
- `none`: Fast, low-latency (default)
- `low`: Simple queries with minimal thinking
- `medium`: Moderate complexity tasks
- `high`: Complex coding, debugging, multi-step planning

### Verbosity Configuration
- `low`: Concise responses
- `medium`: Balanced (default)
- `high`: Detailed explanations

### Safety Limits
- `MAX_TOOL_CALLS_PER_REQUEST`: 20
- `MAX_ITERATIONS`: 10
- `COST_WARNING_THRESHOLD`: $0.50
- `MAX_COST_PER_REQUEST`: $2.00

### System Context
- Current date/time included in every request
- Current working directory included
- System specs cached (5 min) via fastfetch

Configure in `config/settings.py`
