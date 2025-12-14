"""Audio handler for microphone input and speaker output."""
import threading
import queue
import sys
import termios
import tty
import select
from typing import Optional, Callable
from rich.console import Console

console = Console()

# Audio configuration matching Realtime API requirements
SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1024
FORMAT_BITS = 16

# Push-to-talk key (spacebar)
PTT_KEY = " "


class AudioHandler:
    """Handles microphone input and speaker output for voice mode."""
    
    def __init__(self, push_to_talk: bool = False):
        """
        Initialize the audio handler.
        
        Args:
            push_to_talk: If True, only send audio while PTT key is held
        """
        self.pyaudio = None
        self.input_stream = None
        self.output_stream = None
        
        # Queues for audio data
        self.output_queue = queue.Queue()
        
        # Callbacks
        self.on_audio_input: Optional[Callable[[bytes], None]] = None
        
        # Thread control
        self._stop_event = threading.Event()
        self._input_thread: Optional[threading.Thread] = None
        self._output_thread: Optional[threading.Thread] = None
        self._ptt_thread: Optional[threading.Thread] = None
        
        # State
        self.is_recording = False
        self.is_playing = False
        
        # Push-to-talk state
        self.push_to_talk = push_to_talk
        self.ptt_active = False  # True when PTT key is held
        self._old_terminal_settings = None
    
    def initialize(self) -> bool:
        """
        Initialize PyAudio and audio streams.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            import pyaudio
            self.pyaudio = pyaudio.PyAudio()
            
            # Get default input device info
            try:
                default_input = self.pyaudio.get_default_input_device_info()
                console.print(f"[dim]Input device: {default_input['name']}[/dim]")
            except Exception:
                console.print("[yellow]Warning: Could not get default input device[/yellow]")
            
            # Get default output device info
            try:
                default_output = self.pyaudio.get_default_output_device_info()
                console.print(f"[dim]Output device: {default_output['name']}[/dim]")
            except Exception:
                console.print("[yellow]Warning: Could not get default output device[/yellow]")
            
            return True
            
        except ImportError:
            console.print("[red]Error: PyAudio not installed.[/red]")
            console.print("[yellow]Install with: pip install pyaudio[/yellow]")
            console.print("[dim]On Linux, you may need: sudo apt-get install portaudio19-dev[/dim]")
            console.print("[dim]On macOS: brew install portaudio[/dim]")
            return False
        except Exception as e:
            console.print(f"[red]Error initializing audio: {e}[/red]")
            return False
    
    def start_recording(self) -> bool:
        """
        Start recording from microphone.
        
        Returns:
            bool: True if recording started successfully
        """
        if not self.pyaudio:
            console.print("[red]Audio not initialized[/red]")
            return False
        
        try:
            import pyaudio
            
            self.input_stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            self._stop_event.clear()
            self.is_recording = True
            
            # Start input thread
            self._input_thread = threading.Thread(target=self._record_loop, daemon=True)
            self._input_thread.start()
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error starting recording: {e}[/red]")
            return False
    
    def _record_loop(self):
        """Loop to read audio from microphone."""
        while not self._stop_event.is_set() and self.is_recording:
            try:
                if self.input_stream and self.input_stream.is_active():
                    audio_data = self.input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    # Only send audio if PTT is disabled or PTT key is held
                    if self.on_audio_input and (not self.push_to_talk or self.ptt_active):
                        self.on_audio_input(audio_data)
            except Exception as e:
                if not self._stop_event.is_set():
                    console.print(f"[red]Recording error: {e}[/red]")
                break
    
    def _ptt_loop(self):
        """Loop to monitor push-to-talk key state."""
        try:
            # Save terminal settings and switch to raw mode
            fd = sys.stdin.fileno()
            self._old_terminal_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            
            was_active = False
            
            while not self._stop_event.is_set():
                # Check if key is available (non-blocking)
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    key = sys.stdin.read(1)
                    
                    if key == PTT_KEY:
                        if not self.ptt_active:
                            self.ptt_active = True
                            if not was_active:
                                console.print("[green]🎤 Recording...[/green]", end="\r")
                                was_active = True
                    elif key == "\x03":  # Ctrl+C
                        self._stop_event.set()
                        break
                else:
                    # No key pressed - release PTT
                    if self.ptt_active:
                        self.ptt_active = False
                        if was_active:
                            console.print("[dim]   Release to stop[/dim]", end="\r")
                            was_active = False
                            
        except Exception as e:
            if not self._stop_event.is_set():
                console.print(f"[red]PTT error: {e}[/red]")
        finally:
            # Restore terminal settings
            if self._old_terminal_settings:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, self._old_terminal_settings)
                except Exception:
                    pass
    
    def stop_recording(self):
        """Stop recording from microphone."""
        self.is_recording = False
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception:
                pass
            self.input_stream = None
    
    def start_playback(self) -> bool:
        """
        Start audio playback.
        
        Returns:
            bool: True if playback started successfully
        """
        if not self.pyaudio:
            console.print("[red]Audio not initialized[/red]")
            return False
        
        try:
            import pyaudio
            
            self.output_stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            self.is_playing = True
            
            # Start output thread
            self._output_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._output_thread.start()
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error starting playback: {e}[/red]")
            return False
    
    def _playback_loop(self):
        """Loop to play audio to speakers."""
        while not self._stop_event.is_set() and self.is_playing:
            try:
                audio_data = self.output_queue.get(timeout=0.1)
                if audio_data and self.output_stream and self.output_stream.is_active():
                    self.output_stream.write(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    console.print(f"[red]Playback error: {e}[/red]")
                break
    
    def play_audio(self, audio_data: bytes):
        """
        Queue audio data for playback.
        
        Args:
            audio_data: Raw PCM16 audio bytes
        """
        self.output_queue.put(audio_data)
    
    def clear_playback_queue(self):
        """Clear any pending audio in the playback queue."""
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break
    
    def stop_playback(self):
        """Stop audio playback."""
        self.is_playing = False
        self.clear_playback_queue()
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception:
                pass
            self.output_stream = None
    
    def start(self) -> bool:
        """
        Start both recording and playback.
        
        Returns:
            bool: True if both started successfully
        """
        if not self.initialize():
            return False
        
        if not self.start_playback():
            return False
        
        if not self.start_recording():
            self.stop_playback()
            return False
        
        # Start PTT monitoring if enabled
        if self.push_to_talk:
            self._ptt_thread = threading.Thread(target=self._ptt_loop, daemon=True)
            self._ptt_thread.start()
        
        return True
    
    def stop(self):
        """Stop all audio processing."""
        self._stop_event.set()
        self.stop_recording()
        self.stop_playback()
        
        # Restore terminal settings if PTT was used
        if self._old_terminal_settings:
            try:
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_terminal_settings)
            except Exception:
                pass
            self._old_terminal_settings = None
        
        if self.pyaudio:
            try:
                self.pyaudio.terminate()
            except Exception:
                pass
            self.pyaudio = None
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
