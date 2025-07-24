#!/usr/bin/env python3
"""
Example integration of the audio visualizer with AIDA voice assistant.
This shows how to integrate the visualizer with the main voice processing pipeline.
"""

import sys
import time
import logging
import numpy as np
from pathlib import Path

# Add src to path
sys.path.append('src')

from audio_visualizer import AudioVisualizerManager

class VoiceAssistantWithVisualizer:
    """Example voice assistant with integrated visualizer."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.logger = logging.getLogger(__name__)
        
        # Initialize visualizer
        self.visualizer = AudioVisualizerManager(config_path)
        
        # Voice assistant state
        self.is_listening = False
        self.is_speaking = False
        self.is_processing = False
        
    def start(self):
        """Start the voice assistant and visualizer."""
        self.logger.info("Starting voice assistant with visualizer...")
        
        # Start visualizer
        self.visualizer.start()
        
        # Get visualizer info
        stats = self.visualizer.get_stats()
        if stats['current_visualizer'] == 'web':
            port = stats['active_stats']['port']
            self.logger.info(f"Visualizer available at: http://localhost:{port}")
        
        self.logger.info("Voice assistant started successfully")
    
    def stop(self):
        """Stop the voice assistant and visualizer."""
        self.logger.info("Stopping voice assistant...")
        self.visualizer.stop()
        self.logger.info("Voice assistant stopped")
    
    def start_listening(self):
        """Start listening for voice input."""
        self.logger.info("Started listening...")
        self.is_listening = True
        self.is_speaking = False
        self.visualizer.set_listening_state(True)
        self.visualizer.set_speaking_state(False)
    
    def stop_listening(self):
        """Stop listening for voice input."""
        self.logger.info("Stopped listening")
        self.is_listening = False
        self.visualizer.set_listening_state(False)
    
    def start_speaking(self, text: str):
        """Start speaking response."""
        self.logger.info(f"Speaking: {text}")
        self.is_speaking = True
        self.is_listening = False
        self.visualizer.set_speaking_state(True)
        self.visualizer.set_listening_state(False)
    
    def stop_speaking(self):
        """Stop speaking."""
        self.logger.info("Finished speaking")
        self.is_speaking = False
        self.visualizer.set_speaking_state(False)
    
    def process_audio_chunk(self, audio_data: np.ndarray):
        """Process an audio chunk and update visualizer."""
        # Update visualizer with audio data
        self.visualizer.update_audio_data(audio_data)
        
        # Here you would normally process the audio for speech recognition
        # For this example, we'll just simulate processing
        if self.is_listening:
            # Simulate speech detection
            volume = np.sqrt(np.mean(audio_data ** 2))
            if volume > 0.1:  # Speech detected
                self.logger.debug(f"Speech detected, volume: {volume:.3f}")
    
    def simulate_conversation(self):
        """Simulate a conversation to demonstrate the visualizer."""
        self.logger.info("Starting conversation simulation...")
        
        # Conversation scenarios
        scenarios = [
            {
                "name": "Wake word detection",
                "duration": 3,
                "listening": True,
                "speaking": False,
                "audio_pattern": "wake_word"
            },
            {
                "name": "User speaking",
                "duration": 4,
                "listening": True,
                "speaking": False,
                "audio_pattern": "user_speech"
            },
            {
                "name": "Processing",
                "duration": 2,
                "listening": False,
                "speaking": False,
                "audio_pattern": "quiet"
            },
            {
                "name": "Assistant responding",
                "duration": 5,
                "listening": False,
                "speaking": True,
                "audio_pattern": "assistant_speech"
            },
            {
                "name": "Idle",
                "duration": 3,
                "listening": False,
                "speaking": False,
                "audio_pattern": "ambient"
            }
        ]
        
        for scenario in scenarios:
            self.logger.info(f"Scenario: {scenario['name']}")
            
            # Set states
            if scenario['listening']:
                self.start_listening()
            else:
                self.stop_listening()
            
            if scenario['speaking']:
                self.start_speaking(f"This is the {scenario['name']} phase")
            else:
                self.stop_speaking()
            
            # Generate appropriate audio pattern
            duration = scenario['duration']
            pattern = scenario['audio_pattern']
            
            for i in range(int(duration * 10)):  # 10 FPS
                audio_data = self._generate_audio_pattern(pattern, i * 0.1)
                self.process_audio_chunk(audio_data)
                time.sleep(0.1)
        
        self.logger.info("Conversation simulation completed")
    
    def _generate_audio_pattern(self, pattern: str, t: float) -> np.ndarray:
        """Generate synthetic audio data for different patterns."""
        base_noise = np.random.random(1024) * 0.05  # Background noise
        
        if pattern == "wake_word":
            # Short burst of activity
            if int(t * 2) % 2 == 0:
                return base_noise + np.random.random(1024) * 0.3
            else:
                return base_noise
        
        elif pattern == "user_speech":
            # Variable speech pattern
            speech_intensity = 0.4 + 0.3 * np.sin(t * 3) * np.random.random()
            syllable_pulse = 0.2 if int(t * 4) % 3 == 0 else 0
            return base_noise + np.random.random(1024) * (speech_intensity + syllable_pulse)
        
        elif pattern == "assistant_speech":
            # More consistent speech pattern
            speech_intensity = 0.5 + 0.2 * np.sin(t * 2)
            syllable_pulse = 0.3 if int(t * 5) % 4 == 0 else 0
            return base_noise + np.random.random(1024) * (speech_intensity + syllable_pulse)
        
        elif pattern == "quiet":
            # Very low activity during processing
            return base_noise * 0.5
        
        elif pattern == "ambient":
            # Low ambient noise
            return base_noise
        
        else:
            return base_noise

def main():
    """Main function to run the example."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("AIDA Voice Assistant with Visualizer - Integration Example")
    
    try:
        # Create voice assistant with visualizer
        assistant = VoiceAssistantWithVisualizer()
        
        # Start the assistant
        assistant.start()
        
        # Run conversation simulation
        assistant.simulate_conversation()
        
        # Keep running for manual testing
        logger.info("Assistant is running. Press Ctrl+C to stop.")
        logger.info("You can view the visualizer in your browser.")
        
        try:
            while True:
                # Generate some ambient audio
                ambient_audio = np.random.random(1024) * 0.02
                assistant.process_audio_chunk(ambient_audio)
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        try:
            assistant.stop()
        except:
            pass

if __name__ == "__main__":
    main()