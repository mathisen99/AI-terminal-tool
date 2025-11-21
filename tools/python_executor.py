"""Python code execution tool for calculations and data processing."""
import subprocess
import tempfile
import os
from typing import Optional
import sys
import time

# Tool definition for OpenAI function calling (with strict mode)
python_executor_tool_definition = {
    "type": "function",
    "name": "execute_python",
    "description": "Execute Python code for calculations, data processing, and analysis. Returns stdout, stderr, and exit code. Safe sandbox execution.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Use print() for output. Can import standard library modules.",
            },
            "timeout": {
                "type": ["integer", "null"],
                "description": "Timeout in seconds. Default: 30, Max: 300",
            },
        },
        "required": ["code", "timeout"],
        "additionalProperties": False
    },
    "strict": True
}


def validate_code_safety(code: str) -> tuple[bool, Optional[str]]:
    """
    Validate that code doesn't contain dangerous operations.
    
    Args:
        code: Python code to validate
    
    Returns:
        Tuple of (is_safe, error_message)
    """
    # Dangerous patterns to block
    dangerous_patterns = [
        "os.system",
        "subprocess",
        "exec(",
        "eval(",
        "__import__",
        "open(",
        "compile(",
        "globals()",
        "locals()",
        "vars(",
        "dir(",
        "__builtins__",
        "getattr(",
        "setattr(",
        "delattr(",
        "type(",
        "object.__subclasses__",
        "importlib",
        "pkgutil",
        "inspect",
        "ctypes",
        "socket",
        "urllib",
        "requests",
        "http.client",
        "ftplib",
        "telnetlib",
        "ssl",
        "pickle",
        "marshal",
        "shelve",
        "dbm",
        "sqlite3",
        "psycopg2",
        "pymongo",
        "redis",
    ]
    
    code_lower = code.lower()
    
    for pattern in dangerous_patterns:
        if pattern in code_lower:
            return False, f"Dangerous operation blocked: '{pattern}' is not allowed"
    
    return True, None


def execute_python(code: str, timeout: Optional[int] = None) -> str:
    """
    Execute Python code in a safe sandbox environment.
    
    Args:
        code: Python code to execute
        timeout: Timeout in seconds (default: 30, max: 300)
    
    Returns:
        Formatted string with output, errors, and exit code
    """
    # Set default timeout
    if timeout is None:
        timeout = 30
    elif timeout > 300:
        timeout = 300  # Cap at 5 minutes
    
    # Validate code safety
    is_safe, error_msg = validate_code_safety(code)
    if not is_safe:
        return f"❌ Error: Code validation failed\n\nReason: {error_msg}\n\n💡 For security reasons, certain operations are not allowed in the Python executor."
    
    # Create temporary file for code
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Execute code
        start_time = time.time()
        
        try:
            process = subprocess.Popen(
                [sys.executable, temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = -1
            duration = time.time() - start_time
            
            return f"❌ Error: Code execution timed out\n\nTimeout: {timeout}s\nDuration: {duration:.2f}s\n\n💡 Suggestion: Optimize your code or increase the timeout value."
        
        duration = time.time() - start_time
        
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
        output = f"✓ Code executed successfully\n\n"
        output += f"Exit code: {exit_code}\n"
        output += f"Duration: {duration:.2f}s\n"
        output += f"{'-' * 80}\n\n"
        
        if stdout:
            output += "OUTPUT:\n"
            output += stdout
            if stdout_truncated:
                output += "\n\n[Output truncated at 10,000 characters]"
            output += "\n\n"
        
        if stderr:
            output += "ERRORS/WARNINGS:\n"
            output += stderr
            if stderr_truncated:
                output += "\n\n[Output truncated at 10,000 characters]"
            output += "\n\n"
        
        if not stdout and not stderr:
            output += "(No output)\n\n"
        
        # Add warning for non-zero exit codes
        if exit_code != 0:
            output = output.replace("✓ Code executed successfully", "⚠️  Code completed with errors")
            output += f"💡 Note: Code exited with code {exit_code}, which typically indicates an error.\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error: Code execution failed\n\nError: {str(e)}\n\n💡 Suggestion: Check your code syntax and try again."
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass
