"""Audio handler for microphone input and speaker output."""
import threading
import queue
from typing import Optional, Callable
from rich.console import Console

console = Console()

# Audio configuration matching Realtime API requirements
SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1024
FORMAT_BITS = 16


class AudioHandler:
    """Handles microphone input and speaker output for voice mode."""
    
    def __init__(self):
        """Initialize the audio handler."""
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
        
        # State
        self.is_recording = False
        self.is_playing = False
    
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
                    if self.on_audio_input:
                        self.on_audio_input(audio_data)
            except Exception as e:
                if not self._stop_event.is_set():
                    console.print(f"[red]Recording error: {e}[/red]")
                break
    
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
        
        return True
    
    def stop(self):
        """Stop all audio processing."""
        self._stop_event.set()
        self.stop_recording()
        self.stop_playback()
        
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
