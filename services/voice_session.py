"""Voice session manager combining Realtime API with audio handling."""
import sys
import signal
import threading
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table

from .realtime_service import RealtimeService, UsageStats
from .audio_handler import AudioHandler
from .memory_manager import MemoryManager
from config.settings import COST_WARNING_THRESHOLD, MAX_COST_PER_REQUEST

console = Console()


class VoiceSession:
    """Manages a complete voice interaction session."""
    
    def __init__(
        self,
        ask_mode: bool = False,
        voice: str = "alloy",
        model: str = "gpt-realtime"
    ):
        """
        Initialize the voice session.
        
        Args:
            ask_mode: If True, disable command execution
            voice: Voice for audio output
            model: Realtime model to use
        """
        self.ask_mode = ask_mode
        self.voice = voice
        self.model = model
        
        # Components
        self.realtime: Optional[RealtimeService] = None
        self.audio: Optional[AudioHandler] = None
        self.memory_manager = MemoryManager()
        
        # Session state
        self.running = False
        self.conversation_history = []
        self.current_user_text = ""
        self.current_assistant_text = ""
        self.session_start_time: Optional[datetime] = None
        self.last_usage: Optional[UsageStats] = None
        self.cost_limit_reached = False
        self.cost_warning_shown = False
        
        # Display state
        self._display_lock = threading.Lock()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            console.print("\n[yellow]Shutting down...[/yellow]")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _on_transcript(self, role: str, text: str):
        """Handle transcript updates."""
        with self._display_lock:
            if role == "user":
                self.current_user_text = text
                self.conversation_history.append({
                    "role": "user",
                    "content": text,
                    "timestamp": datetime.now().isoformat()
                })
                console.print(f"\n[bold cyan]You:[/bold cyan] {text}")
            else:
                self.current_assistant_text = text
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": text,
                    "timestamp": datetime.now().isoformat()
                })
                console.print(f"\n[bold green]Lolo:[/bold green] {text}")
    
    def _on_audio_delta(self, audio_data: bytes):
        """Handle audio output from the model."""
        if self.audio:
            self.audio.play_audio(audio_data)
    
    def _on_error(self, error: str):
        """Handle errors."""
        console.print(f"[red]Error: {error}[/red]")
    
    def _on_session_created(self, event: dict):
        """Handle session creation."""
        session_id = event.get("session", {}).get("id", "unknown")
        console.print(f"[dim]Session ID: {session_id}[/dim]")
    
    def _on_response_done(self, event: dict, usage: UsageStats):
        """Handle response completion and display usage."""
        self.last_usage = usage
        self._display_usage(usage)
        self._check_cost_limits(usage)
    
    def _display_usage(self, usage: UsageStats):
        """Display usage statistics after each response."""
        # Compact one-line usage display
        audio_in = usage.input_audio_tokens
        audio_out = usage.output_audio_tokens
        text_in = usage.input_tokens
        text_out = usage.output_tokens
        cost = usage.total_cost
        
        # Color based on cost level
        if cost >= MAX_COST_PER_REQUEST:
            cost_color = "red"
        elif cost >= COST_WARNING_THRESHOLD:
            cost_color = "yellow"
        else:
            cost_color = "dim"
        
        console.print(
            f"[{cost_color}]💰 Audio: {audio_in:,}→{audio_out:,} | "
            f"Text: {text_in:,}→{text_out:,} | "
            f"Total: ${cost:.4f}[/{cost_color}]"
        )
    
    def _check_cost_limits(self, usage: UsageStats):
        """Check if cost limits have been exceeded."""
        cost = usage.total_cost
        
        # Hard limit - stop session
        if cost >= MAX_COST_PER_REQUEST:
            self.cost_limit_reached = True
            console.print()
            console.print(Panel(
                f"[red]Cost limit reached: ${cost:.4f} >= ${MAX_COST_PER_REQUEST:.2f}[/red]\n\n"
                "Session will end to prevent excessive costs.",
                title="[bold red]❌ Cost Limit Exceeded[/bold red]",
                border_style="red"
            ))
            self.running = False
            return
        
        # Warning threshold
        if cost >= COST_WARNING_THRESHOLD and not self.cost_warning_shown:
            self.cost_warning_shown = True
            console.print()
            console.print(Panel(
                f"[yellow]High cost detected: ${cost:.4f}[/yellow]\n\n"
                f"Approaching limit of ${MAX_COST_PER_REQUEST:.2f}. "
                "Consider ending the session soon.",
                title="[bold yellow]⚠️  Cost Warning[/bold yellow]",
                border_style="yellow"
            ))
    
    def _display_welcome(self):
        """Display welcome message and instructions."""
        mode_text = "[yellow]Ask-Only Mode 🔒[/yellow]" if self.ask_mode else "[green]Normal Mode[/green]"
        
        welcome_content = f"""[bold]Voice Mode Active[/bold]

Mode: {mode_text}
Voice: [cyan]{self.voice}[/cyan]
Model: [cyan]{self.model}[/cyan]

[bold]Instructions:[/bold]
• Speak naturally - the AI will respond with voice and text
• Press [bold]Ctrl+C[/bold] to exit
• Say "goodbye" or "exit" to end the session

[dim]Listening...[/dim]"""
        
        panel = Panel(
            welcome_content,
            title="[bold cyan]🎤 Lolo Voice Assistant[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()
    
    def _display_session_summary(self):
        """Display session summary on exit."""
        if not self.conversation_history and not self.last_usage:
            return
        
        duration = datetime.now() - self.session_start_time if self.session_start_time else None
        
        table = Table(title="[bold]Session Summary[/bold]", show_header=False, box=None)
        table.add_column("Metric", style="cyan", justify="right")
        table.add_column("Value", style="white")
        
        table.add_row("Messages", str(len(self.conversation_history)))
        if duration:
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            table.add_row("Duration", f"{minutes}m {seconds}s")
        table.add_row("Mode", "Ask-Only" if self.ask_mode else "Normal")
        
        # Add usage stats if available
        if self.last_usage:
            table.add_row("Responses", str(self.last_usage.response_count))
            table.add_row("Audio tokens (in)", f"{self.last_usage.input_audio_tokens:,}")
            table.add_row("Audio tokens (out)", f"{self.last_usage.output_audio_tokens:,}")
            table.add_row("Text tokens (in)", f"{self.last_usage.input_tokens:,}")
            table.add_row("Text tokens (out)", f"{self.last_usage.output_tokens:,}")
            if self.last_usage.cached_tokens > 0:
                table.add_row("Cached tokens", f"{self.last_usage.cached_tokens:,}")
            table.add_row("Total cost", f"[green]${self.last_usage.total_cost:.4f}[/green]")
        
        console.print()
        console.print(table)
    
    def start(self) -> bool:
        """
        Start the voice session.
        
        Returns:
            bool: True if session started successfully
        """
        self._setup_signal_handlers()
        self.session_start_time = datetime.now()
        
        # Initialize audio handler
        console.print("[cyan]Initializing audio...[/cyan]")
        self.audio = AudioHandler()
        if not self.audio.start():
            console.print("[red]Failed to initialize audio[/red]")
            return False
        
        # Initialize realtime service
        console.print("[cyan]Connecting to Realtime API...[/cyan]")
        self.realtime = RealtimeService(
            model=self.model,
            voice=self.voice,
            ask_mode=self.ask_mode
        )
        
        # Set up callbacks
        self.realtime.on_transcript = self._on_transcript
        self.realtime.on_audio_delta = self._on_audio_delta
        self.realtime.on_error = self._on_error
        self.realtime.on_session_created = self._on_session_created
        self.realtime.on_response_done = self._on_response_done
        
        # Connect audio input to realtime service
        self.audio.on_audio_input = self.realtime.send_audio
        
        # Connect to API
        if not self.realtime.connect():
            console.print("[red]Failed to connect to Realtime API[/red]")
            self.audio.stop()
            return False
        
        self.running = True
        self._display_welcome()
        
        return True
    
    def run(self):
        """Run the voice session main loop."""
        if not self.start():
            return
        
        try:
            # Main loop - just keep running until stopped
            while self.running and self.realtime and self.realtime.connected:
                # Check for cost limit
                if self.cost_limit_reached:
                    console.print("\n[red]Session ended due to cost limit.[/red]")
                    break
                
                # Check for exit commands in conversation
                if self.conversation_history:
                    last_user_msg = None
                    for msg in reversed(self.conversation_history):
                        if msg["role"] == "user":
                            last_user_msg = msg["content"].lower()
                            break
                    
                    if last_user_msg and any(word in last_user_msg for word in ["goodbye", "exit", "quit", "bye"]):
                        console.print("\n[yellow]Ending session...[/yellow]")
                        break
                
                # Small sleep to prevent busy loop
                import time
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted[/yellow]")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the voice session."""
        self.running = False
        
        if self.realtime:
            self.realtime.disconnect()
            self.realtime = None
        
        if self.audio:
            self.audio.stop()
            self.audio = None
        
        self._display_session_summary()
        
        # Save conversation to memory
        if self.conversation_history or self.last_usage:
            memory = self.memory_manager.load_memory()
            
            # Get usage stats
            usage = self.last_usage or UsageStats()
            
            conversation_data = {
                "timestamp": self.session_start_time.isoformat() if self.session_start_time else datetime.now().isoformat(),
                "question": "[Voice Session]",
                "response": f"Voice conversation with {len(self.conversation_history)} messages",
                "tools_used": [],
                "tokens": {
                    "input": usage.input_tokens + usage.input_audio_tokens,
                    "output": usage.output_tokens + usage.output_audio_tokens,
                    "cached": usage.cached_tokens,
                    "reasoning": 0
                },
                "cost": usage.total_cost,
                "model": self.model,
                "reasoning_effort": "none",
                "mode": "voice-ask" if self.ask_mode else "voice"
            }
            self.memory_manager.add_conversation(memory, conversation_data)


def run_voice_mode(ask_mode: bool = False, voice: str = "alloy"):
    """
    Run the voice mode session.
    
    Args:
        ask_mode: If True, disable command execution
        voice: Voice for audio output
    """
    session = VoiceSession(ask_mode=ask_mode, voice=voice)
    session.run()
