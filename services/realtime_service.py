"""Realtime API service for voice interactions via WebSocket."""
import os
import json
import base64
import threading
import queue
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from rich.console import Console

console = Console()

# Audio configuration
SAMPLE_RATE = 24000  # OpenAI Realtime API uses 24kHz
CHANNELS = 1
CHUNK_SIZE = 1024


@dataclass
class UsageStats:
    """Track usage statistics for a realtime session."""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    input_audio_tokens: int = 0
    output_audio_tokens: int = 0
    total_cost: float = 0.0
    response_count: int = 0
    
    def calculate_cost(self, model: str) -> float:
        """Calculate cost based on token usage and model pricing."""
        from config.settings import REALTIME_PRICING
        
        pricing = REALTIME_PRICING.get(model, REALTIME_PRICING.get("gpt-realtime"))
        if not pricing:
            return 0.0
        
        # Total input = text + audio tokens
        total_input = self.input_tokens + self.input_audio_tokens
        total_output = self.output_tokens + self.output_audio_tokens
        
        # Cached tokens are billed at reduced rate, subtract from full-price input
        non_cached_input = max(0, total_input - self.cached_tokens)
        
        input_cost = non_cached_input * pricing["input"] / 1_000_000
        cached_cost = self.cached_tokens * pricing["cached"] / 1_000_000
        output_cost = total_output * pricing["output"] / 1_000_000
        
        return input_cost + cached_cost + output_cost


class RealtimeService:
    """Service for handling OpenAI Realtime API WebSocket connections."""
    
    def __init__(
        self,
        model: str = "gpt-realtime",
        voice: str = "alloy",
        instructions: Optional[str] = None,
        ask_mode: bool = False
    ):
        """
        Initialize the Realtime service.
        
        Args:
            model: The realtime model to use
            voice: Voice for audio output (alloy, echo, fable, onyx, nova, shimmer)
            instructions: System instructions for the model
            ask_mode: If True, disable command execution tools
        """
        self.model = model
        self.voice = voice
        self.instructions = instructions
        self.ask_mode = ask_mode
        self.ws = None
        self.connected = False
        self.session_id = None
        
        # Audio queues
        self.audio_input_queue = queue.Queue()
        self.audio_output_queue = queue.Queue()
        
        # Event callbacks
        self.on_transcript: Optional[Callable[[str, str], None]] = None  # (role, text)
        self.on_audio_delta: Optional[Callable[[bytes], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_session_created: Optional[Callable[[Dict], None]] = None
        self.on_response_done: Optional[Callable[[Dict, UsageStats], None]] = None  # (event, usage)
        self.on_interrupted: Optional[Callable[[], None]] = None  # Called when user interrupts
        
        # State tracking
        self.is_speaking = False
        self.current_response_text = ""
        self.current_audio_transcript = ""
        
        # Usage tracking
        self.usage = UsageStats()
        
        # Thread control
        self._stop_event = threading.Event()
        self._ws_thread: Optional[threading.Thread] = None
        self._audio_send_thread: Optional[threading.Thread] = None
    
    def connect(self) -> bool:
        """
        Connect to the Realtime API via WebSocket.
        
        Returns:
            bool: True if connection successful
        """
        try:
            import websocket
        except ImportError:
            console.print("[red]Error: websocket-client not installed. Run: pip install websocket-client[/red]")
            return False
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            console.print("[red]Error: OPENAI_API_KEY not set[/red]")
            return False
        
        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        
        self.ws = websocket.WebSocketApp(
            url,
            header=[f"Authorization: Bearer {api_key}"],
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Start WebSocket in a separate thread
        self._stop_event.clear()
        self._ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._ws_thread.start()
        
        # Wait for connection
        import time
        timeout = 10
        start = time.time()
        while not self.connected and time.time() - start < timeout:
            time.sleep(0.1)
        
        return self.connected
    
    def _run_websocket(self):
        """Run the WebSocket connection."""
        self.ws.run_forever()
    
    def _on_open(self, ws):
        """Handle WebSocket connection opened."""
        self.connected = True
        console.print("[green]✓ Connected to Realtime API[/green]")
        
        # Configure the session
        self._configure_session()
        
        # Start audio sending thread
        self._audio_send_thread = threading.Thread(target=self._audio_send_loop, daemon=True)
        self._audio_send_thread.start()
    
    def _configure_session(self):
        """Send session configuration to the API."""
        from config.settings import get_system_prompt, get_system_info
        import getpass
        import socket
        from datetime import datetime
        
        # Get system prompt based on mode (use the same as CLI)
        instructions = self.instructions or get_system_prompt(ask_mode=self.ask_mode)
        
        # Log tools being configured
        console.print(f"[dim]Mode: {'ask-only' if self.ask_mode else 'normal'}[/dim]")
        
        # Build tools list based on mode
        tools = self._get_tools()
        
        session_config = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": self.model,
                "instructions": instructions,
                "audio": {
                    "output": {
                        "voice": self.voice
                    }
                }
            }
        }
        
        # Add tools if available
        if tools:
            session_config["session"]["tools"] = tools
            session_config["session"]["tool_choice"] = "auto"
            tool_names = [t.get("name") or t.get("type") for t in tools]
            console.print(f"[dim]Tools: {', '.join(tool_names)}[/dim]")
        
        self._send_event(session_config)
    
    def _get_tools(self) -> list:
        """Get available tools for the realtime session."""
        import os
        from tools import (
            web_search_function_tool_definition,
            web_fetch_tool_definition,
            analyze_image_tool_definition,
            python_executor_tool_definition,
            execute_command_tool_definition,
            generate_image_tool_definition,
            edit_image_tool_definition,
        )
        
        tools = []
        
        # Add web search as a function tool (internally uses OpenAI's web search API)
        tools.append(self._convert_to_realtime_tool(web_search_function_tool_definition))
        
        # Add function tools available in all modes
        tools.append(self._convert_to_realtime_tool(web_fetch_tool_definition))
        tools.append(self._convert_to_realtime_tool(python_executor_tool_definition))
        tools.append(self._convert_to_realtime_tool(analyze_image_tool_definition))
        
        # Add image generation/editing tools only if BFL_API_KEY is set
        if os.environ.get("BFL_API_KEY"):
            tools.append(self._convert_to_realtime_tool(generate_image_tool_definition))
            tools.append(self._convert_to_realtime_tool(edit_image_tool_definition))
        
        # Add command execution only if not in ask mode
        if not self.ask_mode:
            tools.append(self._convert_to_realtime_tool(execute_command_tool_definition))
        
        return tools
    
    def _convert_to_realtime_tool(self, tool_def: dict) -> dict:
        """Convert a standard tool definition to Realtime API format."""
        if tool_def.get("type") == "function":
            # Check if it's the new format (name at top level) or old format (inside function key)
            if "name" in tool_def:
                # New format - name is at top level
                return {
                    "type": "function",
                    "name": tool_def.get("name"),
                    "description": tool_def.get("description"),
                    "parameters": tool_def.get("parameters", {})
                }
            else:
                # Old format - name is inside function key
                func = tool_def.get("function", {})
                return {
                    "type": "function",
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "parameters": func.get("parameters", {})
                }
        return tool_def
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            event = json.loads(message)
            event_type = event.get("type", "")
            
            # Handle different event types
            if event_type == "session.created":
                self.session_id = event.get("session", {}).get("id")
                if self.on_session_created:
                    self.on_session_created(event)
                    
            elif event_type == "session.updated":
                console.print("[dim]Session configured[/dim]")
                
            elif event_type == "conversation.item.input_audio_transcription.completed":
                # User's speech transcribed
                transcript = event.get("transcript", "")
                if transcript and self.on_transcript:
                    self.on_transcript("user", transcript)
                    
            elif event_type == "response.output_audio_transcript.delta":
                # Assistant's audio transcript delta
                delta = event.get("delta", "")
                self.current_audio_transcript += delta
                
            elif event_type == "response.output_audio_transcript.done":
                # Assistant's audio transcript complete
                transcript = event.get("transcript", self.current_audio_transcript)
                if transcript and self.on_transcript:
                    self.on_transcript("assistant", transcript)
                self.current_audio_transcript = ""
                
            elif event_type == "response.output_text.delta":
                # Text response delta
                delta = event.get("delta", "")
                self.current_response_text += delta
                
            elif event_type == "response.output_text.done":
                # Text response complete
                text = event.get("text", self.current_response_text)
                if text and self.on_transcript:
                    self.on_transcript("assistant", text)
                self.current_response_text = ""
                
            elif event_type == "response.output_audio.delta":
                # Audio output delta
                audio_b64 = event.get("delta", "")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    self.audio_output_queue.put(audio_bytes)
                    if self.on_audio_delta:
                        self.on_audio_delta(audio_bytes)
                        
            elif event_type == "response.done":
                self.is_speaking = False
                self._process_usage(event)
                if self.on_response_done:
                    self.on_response_done(event, self.usage)
                    
            elif event_type == "response.function_call_arguments.done":
                # Handle function call
                self._handle_function_call(event)
                
            elif event_type == "error":
                error_msg = event.get("error", {}).get("message", "Unknown error")
                # Suppress harmless cancellation errors (happens when user speaks but no response is active)
                if "no active response" in error_msg.lower():
                    pass  # Ignore - this is expected when cancelling during silence
                else:
                    console.print(f"[red]API Error: {error_msg}[/red]")
                    if self.on_error:
                        self.on_error(error_msg)
                    
            elif event_type == "input_audio_buffer.speech_started":
                # User started speaking - interrupt any ongoing response (barge-in)
                self.is_speaking = False
                # Cancel the current response to stop audio generation
                self._send_event({"type": "response.cancel"})
                # Clear audio output queue
                while not self.audio_output_queue.empty():
                    try:
                        self.audio_output_queue.get_nowait()
                    except queue.Empty:
                        break
                # Notify callback to clear audio handler queue too
                if self.on_interrupted:
                    self.on_interrupted()
                        
            elif event_type == "input_audio_buffer.speech_stopped":
                # User stopped speaking
                pass
                
        except json.JSONDecodeError as e:
            console.print(f"[red]Failed to parse message: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Error handling message: {e}[/red]")
    
    def _process_usage(self, event: dict):
        """Process usage information from response.done event."""
        response = event.get("response", {})
        usage = response.get("usage", {})
        
        if usage:
            # Extract token counts
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            # Get detailed breakdown if available
            # Try both naming conventions (input_token_details and input_tokens_details)
            input_details = usage.get("input_token_details", usage.get("input_tokens_details", {}))
            output_details = usage.get("output_token_details", usage.get("output_tokens_details", {}))
            
            cached_tokens = input_details.get("cached_tokens", 0)
            audio_input = input_details.get("audio_tokens", 0)
            text_input = input_details.get("text_tokens", 0)
            
            audio_output = output_details.get("audio_tokens", 0)
            text_output = output_details.get("text_tokens", 0)
            
            # Update cumulative usage
            # For text: use text_tokens if available, otherwise calculate from total - audio
            self.usage.input_tokens += text_input if text_input else max(0, input_tokens - audio_input)
            self.usage.output_tokens += text_output if text_output else max(0, output_tokens - audio_output)
            self.usage.cached_tokens += cached_tokens
            self.usage.input_audio_tokens += audio_input
            self.usage.output_audio_tokens += audio_output
            self.usage.response_count += 1
            
            # Calculate total cost
            self.usage.total_cost = self.usage.calculate_cost(self.model)
    
    def _handle_function_call(self, event):
        """Handle a function call from the model."""
        call_id = event.get("call_id")
        name = event.get("name")
        arguments = event.get("arguments", "{}")
        
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            args = {}
        
        # Tool icons for display
        tool_icons = {
            "web_search": "🔍",
            "fetch_webpage": "🌐",
            "analyze_image": "🖼️",
            "generate_image": "🎨",
            "edit_image": "✏️",
            "execute_command": "💻",
            "execute_python": "🐍"
        }
        icon = tool_icons.get(name, "🔧")
        console.print(f"[yellow]{icon} Tool: {name}[/yellow]")
        
        # Long-running tools that need to run in background thread to avoid WebSocket timeout
        long_running_tools = {"generate_image", "edit_image"}
        
        if name in long_running_tools:
            # Run in background thread to prevent WebSocket keepalive timeout
            thread = threading.Thread(
                target=self._execute_tool_async,
                args=(call_id, name, args),
                daemon=True
            )
            thread.start()
        else:
            # Execute quick tools synchronously
            result = self._execute_tool(name, args)
            self._send_function_result(call_id, result)
    
    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool and return the result."""
        from tools import (
            web_search,
            fetch_webpage,
            execute_python,
            execute_command,
            analyze_image,
            generate_image,
            edit_image,
        )
        
        try:
            if name == "web_search":
                return web_search(**args)
            elif name == "fetch_webpage":
                return fetch_webpage(**args)
            elif name == "execute_python":
                return execute_python(**args)
            elif name == "analyze_image":
                return analyze_image(**args)
            elif name == "generate_image":
                return generate_image(**args)
            elif name == "edit_image":
                return edit_image(**args)
            elif name == "execute_command":
                if self.ask_mode:
                    return "Command execution is disabled in ask-only mode."
                else:
                    return execute_command(**args)
            else:
                return f"Unknown function: {name}"
        except Exception as e:
            return f"Error executing {name}: {str(e)}"
    
    def _execute_tool_async(self, call_id: str, name: str, args: dict):
        """Execute a long-running tool in background and send result when done."""
        result = self._execute_tool(name, args)
        self._send_function_result(call_id, result)
    
    def _send_function_result(self, call_id: str, result: str):
        """Send function call result back to the API."""
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result if isinstance(result, str) else json.dumps(result)
            }
        }
        self._send_event(event)
        
        # Trigger response generation
        self._send_event({"type": "response.create"})
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        console.print(f"[red]WebSocket error: {error}[/red]")
        if self.on_error:
            self.on_error(str(error))
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed."""
        self.connected = False
        console.print(f"[yellow]Disconnected from Realtime API[/yellow]")
    
    def _send_event(self, event: dict):
        """Send an event to the WebSocket."""
        if self.ws and self.connected:
            self.ws.send(json.dumps(event))
    
    def _audio_send_loop(self):
        """Loop to send audio data to the API."""
        while not self._stop_event.is_set() and self.connected:
            try:
                audio_chunk = self.audio_input_queue.get(timeout=0.1)
                if audio_chunk:
                    # Encode audio as base64 and send
                    audio_b64 = base64.b64encode(audio_chunk).decode("utf-8")
                    event = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_b64
                    }
                    self._send_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                console.print(f"[red]Error sending audio: {e}[/red]")
    
    def send_audio(self, audio_data: bytes):
        """
        Queue audio data to be sent to the API.
        
        Args:
            audio_data: Raw PCM16 audio bytes
        """
        self.audio_input_queue.put(audio_data)
    
    def send_text(self, text: str):
        """
        Send a text message to the conversation.
        
        Args:
            text: Text message to send
        """
        # Create conversation item
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }
        self._send_event(event)
        
        # Trigger response
        self._send_event({"type": "response.create"})
    
    def commit_audio(self):
        """Commit the current audio buffer (manual turn detection)."""
        self._send_event({"type": "input_audio_buffer.commit"})
    
    def cancel_response(self):
        """Cancel the current response."""
        self._send_event({"type": "response.cancel"})
    
    def disconnect(self):
        """Disconnect from the Realtime API."""
        self._stop_event.set()
        if self.ws:
            self.ws.close()
        self.connected = False
