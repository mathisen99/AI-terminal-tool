"""Main entry point for the AI assistant."""
import sys
import argparse
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from config.settings import DEFAULT_MODEL, SYSTEM_PROMPT, MODEL_PRICING
from services import OpenAIService, MemoryManager
from tools import (
    web_search_tool_definition,
    fetch_webpage,
    web_fetch_tool_definition,
)

# Initialize Rich console
console = Console()

# ANSI color codes
class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def calculate_cost(usage, model):
    """Calculate the cost of the API request."""
    if model not in MODEL_PRICING:
        return 0.0
    
    pricing = MODEL_PRICING[model]
    
    # Get token counts
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    cached_tokens = getattr(usage, "input_tokens_cached", 0)
    
    # Calculate cost (pricing is per 1M tokens)
    input_cost = (input_tokens - cached_tokens) * pricing["input"] / 1_000_000
    cached_cost = cached_tokens * pricing["cached"] / 1_000_000
    output_cost = output_tokens * pricing["output"] / 1_000_000
    
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
    # Initialize the OpenAI service
    service = OpenAIService(model=DEFAULT_MODEL)

    # Define available tools (mix of custom functions and built-in tools)
    tools = [
        web_search_tool_definition,
        web_fetch_tool_definition,
    ]

    # Define function handlers (only for custom function tools)
    function_handlers = {
        "fetch_webpage": fetch_webpage,
    }

    # Create initial input with system prompt and conversation history
    input_list = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
    total_cost = 0.0
    tool_calls_made = []

    # Keep processing until we get a final text response
    max_iterations = 5
    iteration = 0

    print(f"{Colors.CYAN}Processing...{Colors.RESET}\n")

    while iteration < max_iterations:
        iteration += 1

        # Get response from model
        response = service.create_response(input_list, tools)

        # Track usage
        if hasattr(response, "usage"):
            usage = response.usage
            total_input_tokens += getattr(usage, "input_tokens", 0)
            total_output_tokens += getattr(usage, "output_tokens", 0)
            total_cached_tokens += getattr(usage, "input_tokens_cached", 0)
            total_cost += calculate_cost(usage, DEFAULT_MODEL)

        # Add response output to input list
        input_list += response.output

        # Check for different types of tool calls
        has_function_calls = False
        has_web_search = False
        has_message = False
        
        for item in response.output:
            if item.type == "function_call":
                has_function_calls = True
                tool_calls_made.append(item.name)
                print(f"{Colors.YELLOW}🔧 Calling tool: {Colors.BOLD}{item.name}{Colors.RESET}")
            elif item.type == "web_search_call":
                has_web_search = True
                tool_calls_made.append("web_search")
                action = getattr(item, "action", None)
                if action and hasattr(action, "query"):
                    print(f"{Colors.YELLOW}🌐 Web search: {Colors.BOLD}{action.query}{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}🌐 Web search performed{Colors.RESET}")
            elif item.type == "message":
                has_message = True

        # Process function calls if any
        if has_function_calls:
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
    print(f"\n{Colors.GREEN}{Colors.BOLD}Response:{Colors.RESET}")
    print(f"{Colors.GREEN}{final_response}{Colors.RESET}\n")
    
    # Display citations if any
    if citations:
        print(f"{Colors.CYAN}{Colors.BOLD}Sources:{Colors.RESET}")
        for i, citation in enumerate(citations, 1):
            title = citation["title"] if citation["title"] else "Source"
            print(f"  {i}. {Colors.CYAN}{title}{Colors.RESET}")
            print(f"     {citation['url']}")
        print()
    
    # Display usage statistics
    print(f"{Colors.BLUE}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}Usage Statistics:{Colors.RESET}")
    print(f"  Model: {Colors.CYAN}{DEFAULT_MODEL}{Colors.RESET}")
    
    if tool_calls_made:
        print(f"  Tools used: {Colors.MAGENTA}{', '.join(set(tool_calls_made))}{Colors.RESET}")
    
    print(f"  Input tokens: {Colors.YELLOW}{total_input_tokens:,}{Colors.RESET}")
    if total_cached_tokens > 0:
        print(f"  Cached tokens: {Colors.YELLOW}{total_cached_tokens:,}{Colors.RESET}")
    print(f"  Output tokens: {Colors.YELLOW}{total_output_tokens:,}{Colors.RESET}")
    print(f"  Total tokens: {Colors.YELLOW}{total_input_tokens + total_output_tokens:,}{Colors.RESET}")
    print(f"  Cost: {Colors.GREEN}${total_cost:.6f}{Colors.RESET}")
    print(f"{Colors.BLUE}{'─' * 60}{Colors.RESET}")
    
    # Return conversation data for memory storage
    return {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "response": final_response,
        "tools_used": list(set(tool_calls_made)),
        "tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "cached": total_cached_tokens
        },
        "cost": total_cost,
        "model": DEFAULT_MODEL
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
        mode_info = f" {Colors.YELLOW}[Ask-Only Mode 🔒]{Colors.RESET}"
    elif args.new:
        mode_info = f" {Colors.CYAN}[New Session]{Colors.RESET}"
    
    print(f"{Colors.BOLD}Question:{Colors.RESET} {question}{mode_info}\n")
    
    try:
        # Process question with memory
        conversation_data = process_question(question, memory_manager, memory, ask_mode=args.ask)
        
        # Save conversation to memory
        memory_manager.add_conversation(memory, conversation_data)
        
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
