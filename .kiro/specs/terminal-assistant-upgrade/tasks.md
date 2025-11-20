# Implementation Plan

- [x] 1. CLI and Memory System
  - [x] 1.1 Implement CLI Argument Parsing
    - Add argparse for command-line arguments
    - Implement default mode (continue conversation)
    - Implement `--new` flag (clear memory)
    - Implement `--ask` flag (read-only mode)
    - Handle question as positional argument
    - Add help text for all arguments
    - Test all CLI combinations
    - _Acceptance Criteria: AC7, AC8_
    - _Estimated Effort: 45 minutes_
  
  - [x] 1.2 Create Memory Manager
    - Create `services/memory_manager.py`
    - Implement `MemoryManager` class
    - Add load_memory() method
    - Add save_memory() method
    - Add add_conversation() method
    - Add clear_memory() method
    - Add get_context_messages() method
    - Create memory directory (~/.lolo/)
    - Implement max conversation limit (50)
    - Add auto-cleanup for old conversations
    - Export from `services/__init__.py`
    - _Acceptance Criteria: AC7_
    - _Estimated Effort: 1.5 hours_
  
  - [x] 1.3 Integrate Memory with Main Loop
    - Load memory at startup (unless --new)
    - Build input context from memory
    - Save conversation after each response
    - Update memory stats (cost, token count)
    - Handle --new flag to clear memory
    - Limit context to last 10 conversations
    - _Acceptance Criteria: AC7_
    - _Estimated Effort: 1 hour_
  
  - [x] 1.4 Display Session Info
    - Create Rich panel for session info
    - Display conversation count (X/50)
    - Display total session cost
    - Display current mode (Normal/Ask-Only)
    - Show at start of each session
    - Add 🔒 emoji for ask-only mode
    - _Acceptance Criteria: AC7, AC12_
    - _Estimated Effort: 45 minutes_

- [x] 2. Core Model Migration
  - [x] 2.1 Update Model Configuration
    - **Reference**: Read `docs/GPT_51.md` for GPT-5.1 configuration
    - Update `config/settings.py` with GPT-5.1 model and pricing
    - Add reasoning effort configuration (`none`, `low`, `medium`, `high`)
    - Add verbosity configuration (`low`, `medium`, `high`)
    - **Add safety limits: MAX_TOOL_CALLS_PER_REQUEST = 20**
    - **Add safety limits: MAX_ITERATIONS = 10**
    - **Add cost limits: COST_WARNING_THRESHOLD = 0.50**
    - **Add cost limits: MAX_COST_PER_REQUEST = 2.00**
    - Update system prompt for GPT-5.1 capabilities
    - Add configuration for default reasoning and verbosity levels
    - _Acceptance Criteria: AC1, AC10_
    - _Estimated Effort: 45 minutes_
    - _Reference Docs: docs/GPT_51.md_
  
  - [x] 2.2 Update System Prompt for Modes
    - **Reference**: Read `docs/GPT_51.md` for prompting best practices
    - Convert SYSTEM_PROMPT to function get_system_prompt()
    - Add ask_mode parameter
    - **Gather system context: current date, time, working directory**
    - **Run fastfetch --pipe to get system info**
    - **Cache system info (refresh every 5 minutes)**
    - Include current working directory in prompt
    - Include current date/time in prompt
    - Include system specs in prompt
    - Update prompt for ask-only mode
    - Add mode-specific guidelines
    - Test both modes
    - _Acceptance Criteria: AC8, AC11_
    - _Estimated Effort: 45 minutes_
    - _Reference Docs: docs/GPT_51.md_
  
  - [x] 2.3 Migrate to Responses API
    - **Reference**: Read `docs/GPT_51.md` for Responses API syntax
    - Update `OpenAIService` to use `responses.create()` instead of old API
    - Add reasoning and verbosity parameters to service methods
    - Update response handling for new output format
    - Handle reasoning items in response output
    - Update token usage tracking for new response format
    - _Acceptance Criteria: AC1_
    - _Estimated Effort: 1 hour_
    - _Reference Docs: docs/GPT_51.md_
  
  - [x] 2.4 Update Main Loop for Responses API
    - Update conversation loop to handle new response types
    - Add reasoning token tracking
    - Update cost calculation for GPT-5.1 pricing
    - Handle new output item types (reasoning, message, etc.)
    - Update display logic for reasoning summaries
    - **Implement tool call counter**
    - **Implement iteration counter**
    - **Check cost limits after each response**
    - **Abort if MAX_TOOL_CALLS_PER_REQUEST exceeded**
    - **Abort if MAX_ITERATIONS exceeded**
    - **Abort if MAX_COST_PER_REQUEST exceeded**
    - **Display warnings for COST_WARNING_THRESHOLD**
    - **Show tool call count and iteration in progress**
    - _Acceptance Criteria: AC1, AC10_
    - _Estimated Effort: 1.5 hours_

- [x] 3. Ask-Only Mode Implementation
  - [x] 3.1 Implement Tool Filtering
    - Create get_available_tools() function
    - Filter tools based on ask_mode flag
    - Exclude execute_command in ask-only mode
    - Include web_search, fetch_webpage, analyze_image
    - Test tool availability in both modes
    - _Acceptance Criteria: AC8_
    - _Estimated Effort: 30 minutes_
  
  - [x] 3.2 Add Ask-Only Mode Indicators
    - Add mode indicator to session info panel
    - Show 🔒 emoji in ask-only mode
    - Display warning if command execution attempted
    - Add mode to conversation memory
    - Test visual indicators
    - _Acceptance Criteria: AC8, AC12_
    - _Estimated Effort: 30 minutes_

- [x] 4. Rich Terminal Output
  - [x] 4.1 Setup Rich Library
    - Add `rich>=13.0.0` to requirements.txt
    - Create Rich console instance in main.py
    - Replace ANSI color codes with Rich styling
    - Create helper functions for common Rich patterns (spinners, tables, panels)
    - Test basic Rich output
    - _Acceptance Criteria: AC12_
    - _Estimated Effort: 45 minutes_
  
  - [x] 4.2 Implement Rich Progress Indicators
    - Add spinner for API calls
    - Add progress indicators for tool execution
    - Implement live updates during long operations
    - Add animated spinners for web searches
    - Create status messages with Rich Text
    - _Acceptance Criteria: AC12_
    - _Estimated Effort: 1 hour_
  
  - [x] 4.3 Create Rich Output Formatting
    - Format model responses with Rich Markdown
    - Create table for usage statistics
    - Create panels for errors and confirmations
    - Format citations with Rich styling
    - Add visual indicators for tool calls (🔧, 🌐, 🖼️, 💻)
    - _Acceptance Criteria: AC12_
    - _Estimated Effort: 1 hour_

- [x] 5. Web Tools Enhancement
  - [x] 5.1 Integrate Web Search Tool
    - **Reference**: Read `docs/web_search.md` for web search tool syntax
    - Add `web_search` tool definition (built-in OpenAI tool)
    - Update response handler to process web search calls
    - Extract and display citations from annotations
    - Format citations with Rich styling
    - Add Rich spinner for web searches
    - _Acceptance Criteria: AC2_
    - _Estimated Effort: 45 minutes_
    - _Reference Docs: docs/web_search.md_
  
  - [x] 5.2 Enhance Web Fetch Tool
    - **Reference**: Read `docs/Function_calling.md` for function tool best practices
    - Add undetected-chromedriver dependency
    - Implement cookie dialog auto-acceptance
    - Add Cloudflare challenge bypass logic
    - Implement retry logic with exponential backoff
    - Add better error messages for different failure types
    - Add Rich progress indicator during fetch
    - Test with various protected sites
    - _Acceptance Criteria: AC3_
    - _Estimated Effort: 2 hours_
    - _Reference Docs: docs/Function_calling.md_

- [x] 6. Image Analysis
  - [x] 6.1 Create Image Analysis Tool
    - **Reference**: Read `docs/image_usage.md` for image analysis syntax
    - Create `tools/image_analysis.py`
    - Implement tool definition with strict mode
    - Add support for file path input (convert to base64)
    - Add support for URL input
    - Implement file size validation (max 50MB)
    - Add format validation (PNG, JPEG, WEBP, GIF)
    - Implement detail level parameter (`low`, `high`, `auto`)
    - Create handler function to format image for API
    - Add token cost calculation for images (see docs for formula)
    - Export from `tools/__init__.py`
    - Add Rich spinner during image analysis
    - _Acceptance Criteria: AC4_
    - _Estimated Effort: 2 hours_
    - _Reference Docs: docs/image_usage.md_

- [x] 7. Terminal Command Execution
  - [x] 7.1 Create Command Execution Tool
    - **Reference**: Read `docs/Function_calling.md` for function tool syntax
    - Create `tools/terminal.py`
    - Implement `execute_command` tool definition with strict mode
    - Create risk classification system
    - Define dangerous command patterns (rm -rf, dd, chmod -R, etc.)
    - Implement command execution with timeout (default 30s, max 300s)
    - Capture stdout, stderr, and exit code
    - Add working directory support (default to cwd where main.py invoked)
    - Handle zsh-specific features
    - Add command chaining support (&&, ||)
    - **Implement output truncation (10,000 chars max)**
    - **Execute as user 'mathisen' (current user)**
    - **Sudo commands work without password (NOPASSWD configured)**
    - **Inherit environment variables from parent process**
    - Format output with Rich styling
    - Add Rich spinner during command execution
    - _Acceptance Criteria: AC5, AC6_
    - _Estimated Effort: 3 hours_
    - _Reference Docs: docs/Function_calling.md_
  
  - [x] 7.2 Add Command Safety Features
    - Implement user confirmation prompt for risky commands
    - Create Rich panel for confirmation dialog
    - Add command logging with timestamps
    - Add timeout handling for long-running commands
    - Implement graceful interrupt handling (Ctrl+C)
    - Add suggestions for safer alternatives
    - Test with various dangerous command patterns
    - _Acceptance Criteria: AC5, AC6_
    - _Estimated Effort: 1.5 hours_
  
  - [x] 7.3 Add Interactive Command Detection
    - Create list of interactive commands (vim, nano, less, more, etc.)
    - Detect commands that require user input
    - Warn if interactive command detected
    - Suggest non-interactive alternatives
    - Add to system prompt: examples of non-interactive commands
    - Test with common interactive commands
    - _Acceptance Criteria: AC5_
    - _Estimated Effort: 45 minutes_

- [x] 8. Integration and Polish
  - [x] 8.1 Update Tool Registration
    - Update `main.py` to register all new tools
    - Update function handlers dictionary
    - Verify tool count is 4 (under 20 limit)
    - Ensure all custom tools have strict mode enabled
    - Update tool choice logic if needed
    - _Acceptance Criteria: AC6_
    - _Estimated Effort: 30 minutes_
  
  - [x] 8.2 Enhance Display and UX
    - Add Rich panels for different message types
    - Create consistent visual language for tool types
    - Add live updates during multi-step operations
    - Display reasoning tokens in usage table
    - Update cost tracking display with Rich table
    - Add tool usage summary at end
    - Improve error message formatting with Rich panels
    - Add success/failure indicators with emojis
    - _Acceptance Criteria: AC12_
    - _Estimated Effort: 1.5 hours_
  
  - [x] 8.3 Create Setup Script
    - Create `setup.sh` script
    - Check for UV installation
    - Create venv if not exists
    - Install dependencies with uv pip
    - Add helpful messages
    - Make script executable
    - Test setup process
    - _Acceptance Criteria: AC12_
    - _Estimated Effort: 30 minutes_
  
  - [x] 8.4 Update Documentation
    - Update README.md with new capabilities
    - Document UV and venv setup
    - Document all tools and their usage
    - Add examples for each tool type
    - Document reasoning and verbosity settings
    - Add safety guidelines for command execution
    - Add screenshots/examples of Rich output
    - Update requirements.txt with all new dependencies
    - Document CLI flags (--new, --ask)
    - Document memory system
    - _Acceptance Criteria: AC10_
    - _Estimated Effort: 45 minutes_
  
  - [x] 8.5 Testing and Validation
    - Verify venv is activated for all tests
    - Test GPT-5.1 integration with different reasoning levels
    - Test web search with citations and Rich formatting
    - Test enhanced web fetch with protected sites
    - Test image analysis with various formats and sizes
    - Test command execution with safe commands
    - Test dangerous command confirmation flow with Rich panel
    - Test command chaining (&&, ||)
    - Test error handling for all tools
    - Verify token counting and cost calculation
    - Test multi-turn conversations with tool usage
    - Test Rich output in different terminal sizes
    - Test spinners and progress indicators
    - Verify all Rich formatting looks good
    - Test memory persistence across sessions
    - Test --new flag clears memory
    - Test --ask flag restricts tools
    - Test conversation count display
    - Test follow-up questions with context
    - Test setup.sh script
    - Verify UV package management works
    - _Acceptance Criteria: All ACs_
    - _Estimated Effort: 2.5 hours_

- [x] 9. Optimization
  - [x] 9.1 Performance Optimization
    - Implement prompt caching strategy
    - Optimize tool descriptions for token efficiency
    - Optimize image token usage
    - Add caching for repeated operations
    - Profile Rich rendering performance
    - Optimize spinner update frequency
    - _Acceptance Criteria: AC12_
    - _Estimated Effort: 1 hour_

## Estimated Total Effort: ~28.75 hours

## Documentation References

**CRITICAL**: Always refer to the docs folder for correct syntax:

| File | Purpose |
|------|---------|
| `docs/GPT_51.md` | GPT-5.1 configuration, Responses API, reasoning, verbosity |
| `docs/Function_calling.md` | Function tool definitions, strict mode, parameters |
| `docs/web_search.md` | Web search tool, citations, sources |
| `docs/image_usage.md` | Image analysis, formats, detail levels, token calculation |

## Critical Issues Addressed

### 1. Sudo Password Handling
**Solution**: User (mathisen) has NOPASSWD configured in sudoers, so sudo commands work without prompts. No special handling needed.

### 2. Long-Running Commands
**Solution**: Configurable timeout (default 30s, max 300s) with Rich progress spinner and Ctrl+C interrupt support.

### 3. Command Output Size
**Solution**: Truncate output at 10,000 characters with clear indication when truncated.

### 4. Working Directory Context
**Solution**: Execute from directory where main.py was invoked, pass cwd to subprocess.

### 5. Environment Variables
**Solution**: Inherit full environment from parent process via os.environ.copy().

### 6. Memory Growth
**Solution**: Only use last 10 conversations for context, store max 50 in memory.json.

### 7. API Rate Limits
**Solution**: Implement retry logic with exponential backoff on rate limit errors.

### 8. Cost Control
**Solution**: Warn at $0.50, abort at $2.00 per request with clear error messages.

### 9. Concurrent Tool Calls
**Solution**: Process tool calls sequentially for safety, handle errors gracefully.

### 10. File Path Resolution
**Solution**: Trust model to use find/ls commands to locate files.

### 11. Excessive Tool Calls
**Solution**: Hard limit of 20 tool calls per request, 10 iterations max, abort with error if exceeded.

### 12. Interactive Commands
**Solution**: Non-interactive only - use --noconfirm flags, sed/echo instead of vim/nano, cat instead of less/more.

## Testing Checklist

### Functional Tests
- [ ] GPT-5.1 responds correctly with different reasoning levels
- [ ] Web search returns citations
- [ ] Web fetch bypasses bot protection
- [ ] Image analysis works with files and URLs
- [ ] Commands execute and return output
- [ ] Dangerous commands trigger confirmation
- [ ] Command chaining works (&&, ||)
- [ ] Error handling works for all tools

### UX Tests
- [ ] Rich spinners display during operations
- [ ] Progress bars work for long operations
- [ ] Tables format correctly
- [ ] Markdown renders properly
- [ ] Colors and styling look good
- [ ] Emojis display correctly
- [ ] Output is readable in different terminal sizes

### Safety Tests
- [ ] `rm -rf` triggers confirmation
- [ ] `dd` commands trigger confirmation
- [ ] `chmod -R 777` triggers confirmation
- [ ] Fork bombs are detected
- [ ] `curl | sh` triggers confirmation
- [ ] Safe commands execute without confirmation
- [ ] Timeout works for long commands
- [ ] Ctrl+C interrupts gracefully

### Interactive Command Tests
- [ ] `vim` is rejected or converted to sed/echo
- [ ] `nano` is rejected or converted to sed/echo
- [ ] `less` is rejected or converted to cat
- [ ] `more` is rejected or converted to cat
- [ ] `pacman -Syu` automatically adds `--noconfirm`
- [ ] `yay -S package` automatically adds `--noconfirm`
- [ ] Interactive command detection works
- [ ] Non-interactive alternatives suggested

### Real-World Use Case Tests
These are just sample tests - the assistant should handle ANY natural language request:
- [ ] "Check system health" → runs appropriate system commands
- [ ] "Update system" → runs pacman -Syu --noconfirm
- [ ] "Disk space left" → runs df -h or similar
- [ ] "Edit .zshrc add alias" → uses echo >> not vim
- [ ] "List all images in home" → runs find with image extensions
- [ ] "Biggest file in home" → runs du | sort | head or similar
- [ ] "Is X program updated" → runs pacman -Qi or similar
- [ ] "Analyze latest screenshot" → finds screenshot, uses analyze_image
- [ ] Test with various other natural language requests
- [ ] Verify model can figure out appropriate commands for any request

### Context Awareness Tests
- [ ] "List files here" → uses current working directory from context
- [ ] "What's today's date?" → uses date from system prompt
- [ ] "How much RAM do I have?" → knows from system info
- [ ] "What GPU do I have?" → knows from system info (RTX 4060 Ti)
- [ ] "What's my CPU?" → knows from system info (Ryzen 9 3900X)
- [ ] Verify system info is cached and not fetched every request
- [ ] Verify working directory changes are reflected

### Environment Tests
- [ ] Venv activation works correctly
- [ ] UV package installation works
- [ ] setup.sh script completes successfully
- [ ] Application runs within venv
- [ ] No system-wide package pollution
- [ ] uv run command works
- [ ] Dependencies install correctly with uv pip
