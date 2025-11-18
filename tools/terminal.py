"""Terminal command execution tool definition and implementation."""
import subprocess
import os
import re
import signal
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

# Initialize Rich console for user prompts
console = Console()

# Tool definition for OpenAI function calling (with strict mode)
# Optimized for token efficiency while maintaining clarity
execute_command_tool_definition = {
    "type": "function",
    "name": "execute_command",
    "description": "Execute zsh command. Supports file ops (cat, ls, sed, grep, echo). Returns stdout, stderr, exit code. Dangerous commands need confirmation. MUST be non-interactive (use --noconfirm; sed/echo not vim/nano; cat not less/more).",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command to run. Chainable with && or ||. Non-interactive only. Ex: 'ls -la', 'cat file.txt', 'sudo pacman -Syu --noconfirm'",
            },
            "working_dir": {
                "type": ["string", "null"],
                "description": "Working dir. Default: current dir",
            },
            "timeout": {
                "type": ["integer", "null"],
                "description": "Timeout (sec). Default: 30, Max: 300",
            },
        },
        "required": ["command", "working_dir", "timeout"],
        "additionalProperties": False
    },
    "strict": True
}


# Dangerous command patterns that require user confirmation
DANGEROUS_PATTERNS = [
    r"rm\s+(-[rf]+|--recursive|--force)\s+",  # rm -rf, rm -fr, etc.
    r"rm\s+.*\s+(-[rf]+|--recursive|--force)",  # rm with -rf anywhere
    r"dd\s+(if=|of=)",  # dd commands
    r"chmod\s+(-R|--recursive)\s+777",  # chmod -R 777
    r"chown\s+(-R|--recursive)",  # chown -R
    r"mkfs\.",  # filesystem creation
    r"fdisk|parted",  # disk partitioning
    r":\(\)\{\s*:\|:&\s*\};:",  # fork bomb
    r"curl\s+.*\|\s*(sh|bash|zsh)",  # curl | sh
    r"wget\s+.*\|\s*(sh|bash|zsh)",  # wget | sh
    r"sudo\s+rm\s+",  # sudo rm
    r">\s*/dev/(sd[a-z]|nvme)",  # writing to disk devices
]

# Interactive commands that should be avoided
INTERACTIVE_COMMANDS = [
    "vim", "vi", "nvim",  # Text editors
    "nano", "emacs", "pico",  # Text editors
    "less", "more",  # Pagers
    "top", "htop", "btop",  # Interactive monitors
    "man",  # Manual pages
    "python", "python3", "ipython",  # Interactive Python (without -c)
    "node",  # Interactive Node.js (without -e)
    "irb", "pry",  # Interactive Ruby
    "mysql", "psql", "sqlite3",  # Interactive database shells (without -c)
]

# Command log file
COMMAND_LOG_FILE = Path.home() / ".lolo" / "command_log.txt"


def get_safer_alternative(command: str) -> Optional[str]:
    """
    Suggest a safer alternative for dangerous commands.
    
    Args:
        command: The dangerous command
    
    Returns:
        Suggested safer alternative or None
    """
    # Check for common dangerous patterns and suggest alternatives
    if re.search(r"rm\s+(-[rf]+|--recursive|--force)", command):
        return "Consider using 'trash' or 'gio trash' to move files to trash instead of permanent deletion. Or use 'rm' without -rf for safer deletion."
    
    if re.search(r"chmod\s+(-R|--recursive)\s+777", command):
        return "Avoid 777 permissions. Use more restrictive permissions like 755 (rwxr-xr-x) or 644 (rw-r--r--)."
    
    if re.search(r"curl\s+.*\|\s*(sh|bash|zsh)", command):
        return "Download the script first, review it, then execute: curl -O <url> && cat script.sh && bash script.sh"
    
    if re.search(r"dd\s+(if=|of=)", command):
        return "Double-check the if= and of= parameters. A mistake can destroy data. Consider using 'rsync' or 'cp' for file copying."
    
    return None


def classify_command_risk(command: str) -> Tuple[str, Optional[str]]:
    """
    Classify the risk level of a command.
    
    Args:
        command: The command to classify
    
    Returns:
        Tuple of (risk_level, reason) where risk_level is "safe", "risky", or "interactive"
    """
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return "risky", f"Matches dangerous pattern: {pattern}"
    
    # Check for interactive commands
    # Split command by pipes and semicolons to check each part
    command_parts = re.split(r'[|;&]', command)
    for part in command_parts:
        # Get the first word (the actual command)
        cmd_word = part.strip().split()[0] if part.strip() else ""
        
        # Remove sudo if present
        if cmd_word == "sudo" and len(part.strip().split()) > 1:
            cmd_word = part.strip().split()[1]
        
        # Check if it's an interactive command
        if cmd_word in INTERACTIVE_COMMANDS:
            # Check if it has non-interactive flags
            if cmd_word in ["vim", "vi", "nvim", "nano", "emacs", "pico"]:
                # These should never be used - suggest alternatives
                return "interactive", f"Interactive editor '{cmd_word}' detected. Use 'sed', 'echo >>', or 'cat >' instead."
            elif cmd_word in ["less", "more"]:
                return "interactive", f"Interactive pager '{cmd_word}' detected. Use 'cat', 'head', or 'tail' instead."
            elif cmd_word in ["top", "htop", "btop"]:
                return "interactive", f"Interactive monitor '{cmd_word}' detected. Use 'ps aux', 'pgrep', or 'systemctl status' instead."
            elif cmd_word in ["man"]:
                return "interactive", f"Interactive manual '{cmd_word}' detected. Use online documentation or 'man {cmd_word} | cat' for non-interactive viewing."
            elif cmd_word in ["python", "python3", "node"] and "-c" not in part and "-e" not in part:
                return "interactive", f"Interactive interpreter '{cmd_word}' detected. Use '-c' flag for non-interactive execution."
            elif cmd_word in ["mysql", "psql", "sqlite3"] and "-c" not in part and "-e" not in part:
                return "interactive", f"Interactive database shell '{cmd_word}' detected. Use '-c' or '-e' flag for non-interactive execution."
            elif cmd_word in ["irb", "pry"]:
                return "interactive", f"Interactive Ruby shell '{cmd_word}' detected. Use 'ruby -e' for non-interactive execution."
    
    # Check for commands that might need --noconfirm
    if re.search(r"(pacman|yay)\s+(-S|-Syu|-R)", command, re.IGNORECASE):
        if "--noconfirm" not in command and "--no-confirm" not in command:
            return "interactive", "Package manager command detected without --noconfirm flag. Add --noconfirm for non-interactive execution."
    
    return "safe", None


def log_command(command: str, working_dir: str, exit_code: int, duration: float, confirmed: bool = False):
    """
    Log command execution to file.
    
    Args:
        command: The command that was executed
        working_dir: Working directory where command was executed
        exit_code: Exit code of the command
        duration: Execution duration in seconds
        confirmed: Whether the command required user confirmation
    """
    try:
        # Ensure log directory exists
        COMMAND_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        confirmed_flag = " [CONFIRMED]" if confirmed else ""
        log_entry = f"[{timestamp}] CWD: {working_dir} | Exit: {exit_code} | Duration: {duration:.2f}s{confirmed_flag} | Command: {command}\n"
        
        # Append to log file
        with open(COMMAND_LOG_FILE, "a") as f:
            f.write(log_entry)
    except Exception:
        # Silently fail if logging doesn't work
        pass


def prompt_user_confirmation(command: str, risk_reason: str) -> bool:
    """
    Prompt user for confirmation before executing a risky command.
    
    Args:
        command: The risky command
        risk_reason: Reason why the command is risky
    
    Returns:
        True if user confirms, False otherwise
    """
    # Create warning panel
    warning_content = f"[bold red]⚠️  DANGEROUS COMMAND DETECTED[/bold red]\n\n"
    warning_content += f"[yellow]Command:[/yellow] [white]{command}[/white]\n\n"
    warning_content += f"[yellow]Risk:[/yellow] {risk_reason}\n\n"
    
    # Add safer alternative if available
    safer_alternative = get_safer_alternative(command)
    if safer_alternative:
        warning_content += f"[cyan]💡 Safer alternative:[/cyan]\n{safer_alternative}\n\n"
    
    warning_content += "[bold]This command could cause data loss or system damage.[/bold]"
    
    panel = Panel(
        warning_content,
        title="[bold red]⚠️  CONFIRMATION REQUIRED[/bold red]",
        border_style="red",
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()
    
    # Prompt for confirmation
    try:
        confirmed = Confirm.ask(
            "[bold yellow]Do you want to proceed with this command?[/bold yellow]",
            default=False
        )
        console.print()
        return confirmed
    except KeyboardInterrupt:
        console.print("\n[red]Command cancelled by user (Ctrl+C)[/red]\n")
        return False
    except Exception:
        # If prompt fails, default to not executing
        return False


def execute_command(command: str, working_dir: Optional[str] = None, timeout: Optional[int] = None) -> str:
    """
    Execute a shell command and return the output.
    
    Args:
        command: The shell command to execute
        working_dir: Working directory for execution (default: cwd where main.py was invoked)
        timeout: Timeout in seconds (default: 30, max: 300)
    
    Returns:
        Formatted string with command output, stderr, and exit code
    """
    import time
    
    # Set default timeout
    if timeout is None:
        timeout = 30
    elif timeout > 300:
        timeout = 300  # Cap at 5 minutes
    
    # Determine working directory
    if working_dir is None:
        # Use ORIGINAL_CWD if set by alias, otherwise use current directory
        working_dir = os.environ.get('ORIGINAL_CWD', os.getcwd())
    else:
        # Expand user home directory
        working_dir = os.path.expanduser(working_dir)
        
        # Verify directory exists
        if not os.path.isdir(working_dir):
            return f"❌ Error: Working directory does not exist\n\nDirectory: {working_dir}\n\n💡 Suggestion: Check the path and ensure the directory exists."
    
    # Classify command risk
    risk_level, risk_reason = classify_command_risk(command)
    
    # Handle interactive commands
    if risk_level == "interactive":
        return f"❌ Error: Interactive command detected\n\nCommand: {command}\n\nReason: {risk_reason}\n\n💡 This command requires user input during execution, which is not supported. Please use the suggested non-interactive alternative."
    
    # Handle risky commands - require user confirmation
    user_confirmed = False
    if risk_level == "risky":
        # Prompt user for confirmation
        confirmed = prompt_user_confirmation(command, risk_reason)
        
        if not confirmed:
            return f"❌ Command cancelled by user\n\nCommand: {command}\n\nReason: {risk_reason}\n\n💡 The command was not executed for safety reasons."
        
        user_confirmed = True
    
    # Prepare environment (inherit from parent process)
    env = os.environ.copy()
    
    # Execute command
    start_time = time.time()
    
    try:
        # Run command with zsh
        process = subprocess.Popen(
            command,
            shell=True,
            executable="/bin/zsh",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            env=env,
            text=True,
            preexec_fn=os.setsid  # Create new process group for better signal handling
        )
        
        # Wait for completion with timeout
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            console.print("\n[yellow]⚠️  Interrupt received (Ctrl+C), terminating command...[/yellow]")
            
            # Kill the process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(0.5)
                
                # Force kill if still running
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    pass
            except:
                pass
            
            stdout, stderr = process.communicate()
            duration = time.time() - start_time
            log_command(command, working_dir, -2, duration, user_confirmed)
            
            return f"⚠️  Command interrupted by user (Ctrl+C)\n\nCommand: {command}\nDuration: {duration:.2f}s\n\n💡 The command was terminated gracefully."
        except subprocess.TimeoutExpired:
            # Kill the process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            time.sleep(0.5)
            
            # Force kill if still running
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except:
                pass
            
            stdout, stderr = process.communicate()
            exit_code = -1
            
            duration = time.time() - start_time
            log_command(command, working_dir, exit_code, duration, user_confirmed)
            
            return f"❌ Error: Command timed out\n\nCommand: {command}\nTimeout: {timeout}s\n\n💡 Suggestion: Increase timeout value or run command in background."
        
        duration = time.time() - start_time
        
        # Log command execution
        log_command(command, working_dir, exit_code, duration, user_confirmed)
        
        # Truncate output if too long (10,000 chars max)
        max_output_length = 10000
        stdout_truncated = False
        stderr_truncated = False
        
        if len(stdout) > max_output_length:
            stdout = stdout[:max_output_length]
            stdout_truncated = True
        
        if len(stderr) > max_output_length:
            stderr = stderr[:max_output_length]
            stderr_truncated = True
        
        # Format output
        output = f"✓ Command executed successfully\n\n"
        output += f"Command: {command}\n"
        output += f"Working directory: {working_dir}\n"
        output += f"Exit code: {exit_code}\n"
        output += f"Duration: {duration:.2f}s\n"
        output += f"{'-' * 80}\n\n"
        
        if stdout:
            output += "STDOUT:\n"
            output += stdout
            if stdout_truncated:
                output += "\n\n[Output truncated at 10,000 characters]"
            output += "\n\n"
        
        if stderr:
            output += "STDERR:\n"
            output += stderr
            if stderr_truncated:
                output += "\n\n[Output truncated at 10,000 characters]"
            output += "\n\n"
        
        if not stdout and not stderr:
            output += "(No output)\n\n"
        
        # Add warning for non-zero exit codes
        if exit_code != 0:
            output = output.replace("✓ Command executed successfully", "⚠️  Command completed with errors")
            output += f"💡 Note: Command exited with code {exit_code}, which typically indicates an error.\n"
        
        return output
        
    except FileNotFoundError:
        return f"❌ Error: Command not found\n\nCommand: {command}\n\n💡 Suggestion: Check if the command is installed and available in PATH."
    
    except PermissionError:
        return f"❌ Error: Permission denied\n\nCommand: {command}\n\n💡 Suggestion: You may need to use 'sudo' or check file permissions."
    
    except Exception as e:
        duration = time.time() - start_time
        log_command(command, working_dir, -1, duration, user_confirmed)
        
        return f"❌ Error: Command execution failed\n\nCommand: {command}\nError: {str(e)}\n\n💡 Suggestion: Check command syntax and try again."
