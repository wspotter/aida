
"""
Advanced Voice Assistant
Main application orchestrating all components for real-time voice interaction.
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

# Import voice assistant components
from core.speech_engine import SpeechEngine
from core.nlp_processor import NLPProcessor
from core.command_handler import CommandHandler
from memory_manager import MemoryManager
from llm_backend import LLMBackend
from computer_controller import ComputerController
from audio_visualizer import AudioVisualizerManager
from utils.config_loader import ConfigLoader


class VoiceAssistant:
    """Advanced voice assistant with real-time processing and local AI."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config_path = config_path
        self.config = ConfigLoader(config_path).get_config()
        
        # Initialize console for rich output
        self.console = Console()
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.speech_engine = None
        self.nlp_processor = None
        self.command_handler = None
        self.memory_manager = None
        self.llm_backend = None
        self.computer_controller = None
        self.visualizer = None
        
        # State management
        self.is_running = False
        self.is_listening = False
        self.conversation_active = False
        self.wake_word = self.config.get("audio", {}).get("wake_word", "assistant")
        
        # Statistics
        self.stats = {
            "start_time": None,
            "total_interactions": 0,
            "successful_interactions": 0,
            "errors": 0,
            "uptime": 0
        }
        
        # Thread management
        self._shutdown_event = threading.Event()
        
        # Initialize components
        self._initialize_components()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """Setup logging with rich formatting."""
        log_level = self.config.get("general", {}).get("log_level", "INFO")
        debug_mode = self.config.get("general", {}).get("debug", False)
        
        if debug_mode:
            log_level = "DEBUG"
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)]
        )
    
    def _initialize_components(self):
        """Initialize all voice assistant components."""
        try:
            self.console.print("[bold blue]Initializing Voice Assistant Components...[/bold blue]")
            
            # Initialize NLP processor
            self.console.print("• Loading NLP processor...")
            self.nlp_processor = NLPProcessor(self.config_path)
            
            # Initialize command handler
            self.console.print("• Loading command handler...")
            self.command_handler = CommandHandler(self.config_path)
            
            # Initialize memory manager
            self.console.print("• Loading memory manager...")
            self.memory_manager = MemoryManager(self.config_path)
            
            # Initialize LLM backend
            self.console.print("• Connecting to LLM backend...")
            self.llm_backend = LLMBackend(self.config_path)
            
            # Initialize computer controller
            self.console.print("• Setting up computer controller...")
            self.computer_controller = ComputerController(self.config_path)
            
            # Initialize audio visualizer
            self.console.print("• Starting audio visualizer...")
            self.visualizer = AudioVisualizerManager(self.config_path)
            
            # Initialize speech engine (last, as it may start audio processing)
            self.console.print("• Initializing speech engine...")
            self.speech_engine = SpeechEngine(self.config_path)
            
            # Setup callbacks
            self.speech_engine.set_audio_callback(self._audio_callback)
            
            self.console.print("[bold green]✓ All components initialized successfully![/bold green]")
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise
    
    def start(self):
        """Start the voice assistant."""
        try:
            self.is_running = True
            self.stats["start_time"] = datetime.now()
            
            self.console.print(Panel.fit(
                "[bold green]🎤 Advanced Voice Assistant Started[/bold green]\n\n"
                f"Wake word: '{self.wake_word}'\n"
                "Say the wake word to start a conversation.\n"
                "Press Ctrl+C to exit.",
                title="Voice Assistant",
                border_style="green"
            ))
            
            # Start visualizer
            if self.visualizer:
                self.visualizer.start()
  
 #           self.visualizer.visualizer.animation_loop()


            
            # Start listening for wake word
            self._start_wake_word_detection()
            
            # Main loop
            self._main_loop()
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Shutting down gracefully...[/yellow]")
        except Exception as e:
            self.logger.error(f"Voice assistant error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the voice assistant."""
        if not self.is_running:
            return
        
        self.is_running = False
        self._shutdown_event.set()
        
        self.console.print("[yellow]Stopping voice assistant...[/yellow]")
        
        # Stop components
        if self.speech_engine:
            self.speech_engine.stop_listening()
            self.speech_engine.cleanup()
        
        if self.visualizer:
            self.visualizer.stop()
        
        # Calculate uptime
        if self.stats["start_time"]:
            self.stats["uptime"] = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        # Show final statistics
        self._show_final_stats()
        
        self.console.print("[bold red]Voice assistant stopped.[/bold red]")
    
    def _start_wake_word_detection(self):
        """Start listening for wake word."""
        if self.speech_engine:
            self.speech_engine.start_listening(self._wake_word_callback)
            self.is_listening = True
            self.logger.info("Wake word detection started")
    
    def _wake_word_callback(self, text: str):
        """Handle wake word detection."""
        if not self.is_running:
            return
        
        text_lower = text.lower().strip()
        
        if self.wake_word.lower() in text_lower:
            self.logger.info(f"Wake word detected: {text}")
            self._start_conversation()
        elif self.conversation_active:
            # Process command during active conversation
            self._process_speech(text)
    
    def _start_conversation(self):
        """Start an active conversation."""
        if self.conversation_active:
            return
        
        self.conversation_active = True
        
        # Update visualizer state
        if self.visualizer:
            self.visualizer.set_listening_state(True)
        
        # Acknowledge wake word
        self.speech_engine.speak("Yes, how can I help you?", blocking=False)
        
        # Set timeout for conversation
        threading.Timer(30.0, self._end_conversation).start()
        
        self.logger.info("Conversation started")
    
    def _end_conversation(self):
        """End the active conversation."""
        if not self.conversation_active:
            return
        
        self.conversation_active = False
        
        # Update visualizer state
        if self.visualizer:
            self.visualizer.set_listening_state(False)
        
        self.logger.info("Conversation ended")
    
    def _process_speech(self, text: str):
        """Process recognized speech."""
        try:
            self.stats["total_interactions"] += 1
            
            self.console.print(f"[bold cyan]User:[/bold cyan] {text}")
            
            # Process with NLP
            nlp_result = self.nlp_processor.process_text(text)
            
            # Handle with command handler first
            command_result = self.command_handler.handle_command(nlp_result)
            
            # If command handler couldn't handle it, use LLM
            if not command_result.get("success", True) or command_result.get("use_llm", False):
                response = self._generate_llm_response(text, nlp_result)
            else:
                response = command_result.get("response", "I'm not sure how to help with that.")
            
            # Store in memory
            if self.memory_manager:
                context = {
                    "nlp_result": nlp_result,
                    "command_result": command_result,
                    "timestamp": datetime.now().isoformat()
                }
                self.memory_manager.store_conversation(text, response, context)
            
            # Speak response
            self.console.print(f"[bold green]Assistant:[/bold green] {response}")
            
            if self.visualizer:
                self.visualizer.set_speaking_state(True)
            
            self.speech_engine.speak(response, blocking=False)
            
            if self.visualizer:
                self.visualizer.set_speaking_state(False)
            
            self.stats["successful_interactions"] += 1
            
            # Extend conversation timeout
            if self.conversation_active:
                threading.Timer(30.0, self._end_conversation).start()
            
        except Exception as e:
            self.logger.error(f"Speech processing error: {e}")
            self.stats["errors"] += 1
            
            error_response = "I'm sorry, I encountered an error processing your request."
            self.speech_engine.speak(error_response, blocking=False)
    
    def _generate_llm_response(self, text: str, nlp_result: Dict[str, Any]) -> str:
        """Generate response using LLM backend."""
        try:
            # Get conversation context from memory
            context = ""
            if self.memory_manager:
                context = self.memory_manager.get_conversation_context(text, max_context=2)
            
            # Generate response
            response = self.llm_backend.generate_response(
                prompt=text,
                context=context,
                system_prompt="You are a helpful voice assistant. Provide concise, conversational responses."
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM response generation failed: {e}")
            return "I'm having trouble connecting to my language model. Let me try to help you with basic commands."
    
    def _audio_callback(self, audio_data: np.ndarray):
        """Handle raw audio data for visualization."""
        if self.visualizer:
            self.visualizer.update_audio_data(audio_data)
    
    def _main_loop(self):
        """Main application loop."""
        try:
            while self.is_running and not self._shutdown_event.is_set():
                # Update statistics
                if self.stats["start_time"]:
                    self.stats["uptime"] = (datetime.now() - self.stats["start_time"]).total_seconds()
                
                # Sleep briefly to prevent busy waiting
                time.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Main loop error: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        self.console.print(f"\n[yellow]Received signal {signum}, shutting down...[/yellow]")
        self.stop()
        sys.exit(0)
    
    def _show_final_stats(self):
        """Show final statistics."""
        table = Table(title="Voice Assistant Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Uptime", f"{self.stats['uptime']:.1f} seconds")
        table.add_row("Total Interactions", str(self.stats["total_interactions"]))
        table.add_row("Successful Interactions", str(self.stats["successful_interactions"]))
        table.add_row("Errors", str(self.stats["errors"]))
        
        if self.stats["total_interactions"] > 0:
            success_rate = (self.stats["successful_interactions"] / self.stats["total_interactions"]) * 100
            table.add_row("Success Rate", f"{success_rate:.1f}%")
        
        self.console.print(table)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all components."""
        status = {
            "running": self.is_running,
            "listening": self.is_listening,
            "conversation_active": self.conversation_active,
            "stats": self.stats.copy(),
            "components": {}
        }
        
        if self.speech_engine:
            status["components"]["speech_engine"] = self.speech_engine.get_status()
        
        if self.nlp_processor:
            status["components"]["nlp_processor"] = self.nlp_processor.get_stats()
        
        if self.command_handler:
            status["components"]["command_handler"] = self.command_handler.get_stats()
        
        if self.memory_manager:
            status["components"]["memory_manager"] = self.memory_manager.get_memory_stats()
        
        if self.llm_backend:
            status["components"]["llm_backend"] = self.llm_backend.get_backend_status()
        
        if self.computer_controller:
            status["components"]["computer_controller"] = self.computer_controller.get_status()
        
        if self.visualizer:
            status["components"]["visualizer"] = self.visualizer.get_stats()
        
        return status


def main():
    """Main entry point for the voice assistant."""
    parser = argparse.ArgumentParser(description="Advanced Voice Assistant")
    parser.add_argument("--config", default="configs/config.json", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-visualizer", action="store_true", help="Disable audio visualizer")
    parser.add_argument("--safety-level", choices=["off", "safer", "god"], help="Computer use safety level")
    
    args = parser.parse_args()
    
    try:
        # Load and modify config if needed
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Configuration file not found: {config_path}")
            sys.exit(1)
        
        # Override config with command line arguments
        if args.debug:
            # Enable debug mode
            pass
        
        if args.no_visualizer:
            # Disable visualizer
            pass
        
        # Create and start voice assistant
        assistant = VoiceAssistant(str(config_path))
        
        # Override safety level if specified
        if args.safety_level and assistant.computer_controller:
            assistant.computer_controller.set_safety_level(args.safety_level)
        
        assistant.start()
        
    except Exception as e:
        print(f"Error starting voice assistant: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
