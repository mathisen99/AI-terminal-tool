"""Main entry point for the AI assistant."""
import sys
import argparse
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from config.settings import (
    DEFAULT_MODEL, 
    DEFAULT_REASONING_EFFORT,
    DEFAULT_VERBOSITY,
    MODEL_PRICING,
    MAX_TOOL_CALLS_PER_REQUEST,
    MAX_ITERATIONS,
    COST_WARNING_THRESHOLD,
    MAX_COST_PER_REQUEST,
    get_system_prompt
)
from services import OpenAIService, MemoryManager
from tools import (
    web_search_tool_definition,
    fetch_webpage,
    web_fetch_tool_definition,
    analyze_image,
    analyze_image_tool_definition,
    execute_command,
    execute_command_tool_definition,
)

# Initialize Rich console
console = Console()


def get_available_tools(ask_mode: bool = False):
    """
    Get available tools based on mode.
    
    Args:
        ask_mode: Whether in ask-only mode
    
    Returns:
        tuple: (tools list, function_handlers dict)
    """
    # Base tools available in all modes
    tools = [
        web_search_tool_definition,
        web_fetch_tool_definition,
        analyze_image_tool_definition,
    ]
    
    # Function handlers for custom function tools
    function_handlers = {
        "fetch_webpage": fetch_webpage,
        "analyze_image": analyze_image,
    }
    
    # In normal mode, add command execution tool
    if not ask_mode:
        tools.append(execute_command_tool_definition)
        function_handlers["execute_command"] = execute_command
    
    return tools, function_handlers


# Rich helper functions for common patterns
def create_spinner(text: str, spinner_type: str = "dots"):
    """Create a Rich spinner with text."""
    return Spinner(spinner_type, text=text)


def create_status_panel(title: str, content: str, style: str = "cyan"):
    """Create a Rich panel for status messages."""
    return Panel(content, title=f"[bold {style}]{title}[/bold {style}]", border_style=style)


def create_error_panel(message: str):
    """Create a Rich panel for error messages."""
    return Panel(f"[red]{message}[/red]", title="[bold red]❌ Error[/bold red]", border_style="red")


def create_warning_panel(message: str):
    """Create a Rich panel for warning messages."""
    return Panel(f"[yellow]{message}[/yellow]", title="[bold yellow]⚠️  Warning[/bold yellow]", border_style="yellow")


def create_success_panel(message: str):
    """Create a Rich panel for success messages."""
    return Panel(f"[green]{message}[/green]", title="[bold green]✓ Success[/bold green]", border_style="green")


def create_usage_table(model: str, tool_calls: list, tool_call_count: int, iteration: int,
                       input_tokens: int, cached_tokens: int, output_tokens: int, 
                       reasoning_tokens: int, cost: float):
    """Create a Rich table for usage statistics."""
    table = Table(title="[bold]Usage Statistics[/bold]", show_header=False, box=None)
    table.add_column("Metric", style="cyan", justify="right")
    table.add_column("Value", style="white")
    
    table.add_row("Model", f"[cyan]{model}[/cyan]")
    
    if tool_calls:
        table.add_row("Tools used", f"[magenta]{', '.join(set(tool_calls))}[/magenta]")
        table.add_row("Tool calls", f"[magenta]{tool_call_count}[/magenta]")
    
    table.add_row("Iterations", f"[cyan]{iteration}[/cyan]")
    table.add_row("Input tokens", f"[yellow]{input_tokens:,}[/yellow]")
    
    if cached_tokens > 0:
        table.add_row("Cached tokens", f"[yellow]{cached_tokens:,}[/yellow]")
    
    table.add_row("Output tokens", f"[yellow]{output_tokens:,}[/yellow]")
    
    if reasoning_tokens > 0:
        table.add_row("Reasoning tokens", f"[yellow]{reasoning_tokens:,}[/yellow]")
    
    total_tokens = input_tokens + output_tokens + reasoning_tokens
    table.add_row("Total tokens", f"[yellow]{total_tokens:,}[/yellow]")
    table.add_row("Cost", f"[green]${cost:.6f}[/green]")
    
    return table


def calculate_cost(usage, model):
    """
    Calculate the cost of the API request including reasoning tokens.
    
    Args:
        usage: Usage object from API response
        model: Model name for pricing lookup
    
    Returns:
        float: Total cost in dollars
    """
    if model not in MODEL_PRICING:
        return 0.0
    
    pricing = MODEL_PRICING[model]
    
    # Get token counts (including reasoning tokens for GPT-5.1)
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    cached_tokens = getattr(usage, "input_tokens_cached", 0)
    reasoning_tokens = getattr(usage, "reasoning_tokens", 0)
    
    # Calculate cost (pricing is per 1M tokens)
    # Reasoning tokens are counted as output tokens
    input_cost = (input_tokens - cached_tokens) * pricing["input"] / 1_000_000
    cached_cost = cached_tokens * pricing["cached"] / 1_000_000
    output_cost = (output_tokens + reasoning_tokens) * pricing["output"] / 1_000_000
    
    total_cost = input_cost + cached_cost + output_cost
    
    return total_cost


def process_question(question: str, memory_manager: MemoryManager, memory: dict, ask_mode: bool = False):
    """
    Process a single question and return the response.
    
    Args:
        question: The user's question
        memory_manager: MemoryManager instance
        memory: Current memory dictionary
        ask_mode: Whether in ask-only mode
    
    Returns:
        Dictionary containing conversation data
    """
    # Initialize the OpenAI service with GPT-5.1 settings
    service = OpenAIService(
        model=DEFAULT_MODEL,
        reasoning=DEFAULT_REASONING_EFFORT,
        verbosity=DEFAULT_VERBOSITY
    )

    # Get available tools based on mode (filters out execute_command in ask-only mode)
    tools, function_handlers = get_available_tools(ask_mode=ask_mode)

    # Get system prompt based on mode
    system_prompt = get_system_prompt(ask_mode=ask_mode)

    # Create initial input with system prompt and conversation history
    input_list = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add conversation history from memory (last 10 conversations)
    context_messages = memory_manager.get_context_messages(memory, limit=10)
    input_list.extend(context_messages)
    
    # Add current question
    input_list.append({"role": "user", "content": question})

    # Track total usage
    total_input_tokens = 0
    total_output_tokens = 0
    total_cached_tokens = 0
    total_reasoning_tokens = 0
    total_cost = 0.0
    tool_calls_made = []
    tool_call_count = 0

    # Keep processing until we get a final text response
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1

        # Display progress with spinner for API call
        status_text = f"[cyan]Iteration {iteration}/{MAX_ITERATIONS} | Tool calls: {tool_call_count}/{MAX_TOOL_CALLS_PER_REQUEST}[/cyan]"
        
        # Use different spinner for web search vs regular API calls
        spinner_type = "earth" if any("web_search" in str(t) for t in tool_calls_made[-3:]) else "dots"
        
        with console.status(f"[bold cyan]Calling API...[/bold cyan] {status_text}", spinner=spinner_type) as status:
            # Get response from model
            response = service.create_response(input_list, tools)
        
        # Track usage
        if hasattr(response, "usage"):
            usage = response.usage
            total_input_tokens += getattr(usage, "input_tokens", 0)
            total_output_tokens += getattr(usage, "output_tokens", 0)
            total_cached_tokens += getattr(usage, "input_tokens_cached", 0)
            total_reasoning_tokens += getattr(usage, "reasoning_tokens", 0)
            
            # Calculate cost for this iteration
            iteration_cost = calculate_cost(usage, DEFAULT_MODEL)
            total_cost += iteration_cost
            
            # Check cost limits
            if total_cost > MAX_COST_PER_REQUEST:
                error_msg = f"Cost limit exceeded: ${total_cost:.2f} > ${MAX_COST_PER_REQUEST:.2f}"
                console.print(create_error_panel(error_msg))
                raise Exception(f"Cost limit exceeded: ${total_cost:.2f}")
            elif total_cost > COST_WARNING_THRESHOLD:
                console.print(f"[yellow]⚠️  Warning: High cost (${total_cost:.2f})[/yellow]")

        # Add response output to input list
        input_list += response.output

        # Check for different types of output items
        has_function_calls = False
        has_web_search = False
        has_message = False
        has_reasoning = False
        
        for item in response.output:
            if item.type == "function_call":
                has_function_calls = True
                tool_call_count += 1
                tool_calls_made.append(item.name)
                
                # Check if command execution attempted in ask-only mode
                if ask_mode and item.name == "execute_command":
                    warning_msg = "Command execution blocked in ask-only mode 🔒\nRestart without --ask flag to enable command execution"
                    console.print(create_warning_panel(warning_msg))
                    # Skip this tool call
                    continue
                
                # Check tool call limit
                if tool_call_count > MAX_TOOL_CALLS_PER_REQUEST:
                    error_msg = f"Too many tool calls: {tool_call_count} > {MAX_TOOL_CALLS_PER_REQUEST}"
                    console.print(create_error_panel(error_msg))
                    raise Exception(f"Tool call limit exceeded: {tool_call_count}")
                
                # Display tool call with appropriate icon
                tool_icons = {
                    "fetch_webpage": "🌐",
                    "analyze_image": "🖼️",
                    "execute_command": "💻"
                }
                icon = tool_icons.get(item.name, "🔧")
                console.print(f"[yellow]{icon} Calling tool: [bold]{item.name}[/bold][/yellow]")
                    
            elif item.type == "web_search_call":
                has_web_search = True
                tool_call_count += 1
                tool_calls_made.append("web_search")
                
                # Check tool call limit
                if tool_call_count > MAX_TOOL_CALLS_PER_REQUEST:
                    error_msg = f"Too many tool calls: {tool_call_count} > {MAX_TOOL_CALLS_PER_REQUEST}"
                    console.print(create_error_panel(error_msg))
                    raise Exception(f"Tool call limit exceeded: {tool_call_count}")
                
                # Display web search with Rich spinner and query details
                action = getattr(item, "action", None)
                if action:
                    query = getattr(action, "query", None)
                    domains = getattr(action, "domains", None)
                    
                    if query:
                        search_text = f"🌐 Searching web: [bold cyan]{query}[/bold cyan]"
                        if domains:
                            search_text += f" [dim](domains: {', '.join(domains[:3])})[/dim]"
                        console.print(f"[yellow]{search_text}[/yellow]")
                    else:
                        console.print("[yellow]🌐 Web search performed[/yellow]")
                else:
                    console.print("[yellow]🌐 Web search performed[/yellow]")
                    
            elif item.type == "message":
                has_message = True
            elif item.type == "reasoning":
                has_reasoning = True
                # Optionally display reasoning summary
                if hasattr(item, "summary") and item.summary:
                    console.print(f"[magenta]💭 Reasoning: {item.summary}[/magenta]")

        # Process function calls if any
        if has_function_calls:
            # Use different spinner and message based on tool type
            for item in response.output:
                if item.type == "function_call":
                    if item.name == "fetch_webpage":
                        spinner_msg = "[bold yellow]🌐 Fetching webpage (bypassing bot protection)...[/bold yellow]"
                        spinner_type = "earth"
                    elif item.name == "analyze_image":
                        spinner_msg = "[bold yellow]🖼️  Analyzing image...[/bold yellow]"
                        spinner_type = "dots"
                    elif item.name == "execute_command":
                        spinner_msg = "[bold yellow]💻 Executing command...[/bold yellow]"
                        spinner_type = "dots"
                    else:
                        spinner_msg = "[bold yellow]🔧 Executing tool...[/bold yellow]"
                        spinner_type = "dots"
                    break
            else:
                spinner_msg = "[bold yellow]Executing tool...[/bold yellow]"
                spinner_type = "dots"
            
            with console.status(spinner_msg, spinner=spinner_type):
                function_outputs = service.process_function_calls(response, function_handlers)
            input_list.extend(function_outputs)
            continue
        
        # If we have web search but no message yet, continue
        if has_web_search and not has_message:
            continue
        
        # If we have a message (with or without web search), we're done
        if has_message:
            break
        
        # No tools and no message - shouldn't happen but break to avoid infinite loop
        break

    # Check if we hit max iterations
    if iteration >= MAX_ITERATIONS:
        warning_msg = f"Reached maximum iterations ({MAX_ITERATIONS})"
        console.print(create_warning_panel(warning_msg))

    # Extract final response and citations
    final_response = ""
    citations = []
    
    if hasattr(response, "output_text") and response.output_text:
        final_response = response.output_text
    
    # Extract citations from message content
    for item in response.output:
        if item.type == "message" and hasattr(item, "content"):
            for content in item.content:
                if hasattr(content, "annotations"):
                    for annotation in content.annotations:
                        if annotation.type == "url_citation":
                            citations.append({
                                "url": annotation.url,
                                "title": getattr(annotation, "title", ""),
                            })
    
    # Display results
    console.print("\n[bold green]Response:[/bold green]")
    console.print(Markdown(final_response))
    console.print()
    
    # Display citations if any with Rich formatting
    if citations:
        console.print()
        console.print("[bold cyan]📚 Sources:[/bold cyan]")
        for i, citation in enumerate(citations, 1):
            title = citation["title"] if citation["title"] else "Source"
            # Create a nicely formatted citation with clickable link
            console.print(f"  [bold cyan]{i}.[/bold cyan] [link={citation['url']}]{title}[/link]")
            console.print(f"     [dim]{citation['url']}[/dim]")
        console.print()
    
    # Display usage statistics using helper function
    usage_table = create_usage_table(
        DEFAULT_MODEL,
        tool_calls_made,
        tool_call_count,
        iteration,
        total_input_tokens,
        total_cached_tokens,
        total_output_tokens,
        total_reasoning_tokens,
        total_cost
    )
    console.print(usage_table)
    
    # Return conversation data for memory storage
    return {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "response": final_response,
        "tools_used": list(set(tool_calls_made)),
        "tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "cached": total_cached_tokens,
            "reasoning": total_reasoning_tokens
        },
        "cost": total_cost,
        "model": DEFAULT_MODEL,
        "reasoning_effort": DEFAULT_REASONING_EFFORT,
        "mode": "ask-only" if ask_mode else "normal"
    }


def display_session_info(memory: dict, ask_mode: bool = False):
    """
    Display session information in a Rich panel.
    
    Args:
        memory: Memory dictionary containing conversation history
        ask_mode: Whether in ask-only mode
    """
    # Get conversation count
    conv_count = len(memory.get("conversations", []))
    max_conv = 50
    
    # Get total session cost
    total_cost = memory.get("total_cost", 0.0)
    
    # Determine mode
    if ask_mode:
        mode = "Ask-Only (Read-Only) 🔒"
        mode_style = "yellow"
    else:
        mode = "Normal"
        mode_style = "green"
    
    # Create table for session info
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")
    
    table.add_row("Conversations in memory:", f"{conv_count}/{max_conv}")
    table.add_row("Total session cost:", f"${total_cost:.4f}")
    table.add_row("Mode:", f"[{mode_style}]{mode}[/{mode_style}]")
    
    # Display panel
    panel = Panel(
        table,
        title="[bold cyan]Session Info[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Lolo - AI Terminal Assistant with GPT-5.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "What's the weather in Paris?"          # Continue previous conversation
  python main.py --new "Tell me about Python"            # Start new session (clear memory)
  python main.py --ask "How do I use sed?"               # Ask-only mode (no system modifications)
        """
    )
    
    parser.add_argument(
        "question",
        nargs="+",
        help="Your question for the AI assistant"
    )
    
    parser.add_argument(
        "--new",
        action="store_true",
        help="Start a new session by clearing conversation memory"
    )
    
    parser.add_argument(
        "--ask",
        action="store_true",
        help="Ask-only mode: read-only, no command execution or file modifications"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Join question parts into a single string
    question = " ".join(args.question)
    
    # Initialize memory manager
    memory_manager = MemoryManager()
    
    # Handle --new flag (clear memory)
    if args.new:
        memory_manager.clear_memory()
    
    # Load memory
    memory = memory_manager.load_memory()
    
    # Display session info at start
    console.print()
    display_session_info(memory, ask_mode=args.ask)
    
    # Display question
    mode_info = ""
    if args.ask:
        mode_info = " [yellow][Ask-Only Mode 🔒][/yellow]"
    elif args.new:
        mode_info = " [cyan][New Session][/cyan]"
    
    console.print(f"[bold]Question:[/bold] {question}{mode_info}\n")
    
    try:
        # Process question with memory
        conversation_data = process_question(question, memory_manager, memory, ask_mode=args.ask)
        
        # Save conversation to memory
        memory_manager.add_conversation(memory, conversation_data)
        
    except Exception as e:
        error_panel = create_error_panel(str(e))
        console.print(error_panel)
        sys.exit(1)


if __name__ == "__main__":
    main()
