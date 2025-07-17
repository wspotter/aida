
"""
Speech recognition and text-to-speech engine.
"""

import json
import logging
import threading
import time
import queue
from pathlib import Path
from typing import Optional, Callable, Dict, Any

import vosk
import pyaudio
import pyttsx3
import numpy as np

from   utils.config_loader import ConfigLoader
from   utils.audio_utils import AudioProcessor


class SpeechEngine:
    """Real-time speech recognition and text-to-speech engine."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.audio_config = self.config.get("audio", {})
        self.tts_config = self.config.get("tts", {})
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Audio parameters
        self.sample_rate = self.audio_config.get("sample_rate", 16000)
        self.chunk_size = self.audio_config.get("chunk_size", 4096)
        self.channels = self.audio_config.get("channels", 1)
        self.device_index = self.audio_config.get("device_index")
        
        # Speech recognition
        self.vosk_model = None
        self.recognizer = None
        self.audio_processor = AudioProcessor()
        
        # Text-to-speech
        self.tts_engine = None
        self.available_voices = []
        
        # Audio streaming
        self.audio_stream = None
        self.pyaudio_instance = None
        self.is_listening = False
        self.is_speaking = False
        
        # Callbacks
        self.speech_callback = None
        self.audio_callback = None
        
        # Threading
        self._lock = threading.RLock()
        self._listen_thread = None
        self._audio_queue = queue.Queue()
        
        # Initialize components
        self._initialize_vosk()
        self._initialize_tts()
        self._initialize_audio()
    
    def _initialize_vosk(self):
        """Initialize Vosk speech recognition."""
        try:
            # Look for Vosk model
            model_path = Path("models/vosk/vosk-model-en")
            if not model_path.exists():
                self.logger.error(f"Vosk model not found at {model_path}")
                return
            
            # Load model
            self.vosk_model = vosk.Model(str(model_path))
            self.recognizer = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
            
            self.logger.info("Vosk speech recognition initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Vosk: {e}")
    
    def _initialize_tts(self):
        """Initialize text-to-speech engine."""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure TTS
            rate = self.tts_config.get("rate", 180)
            volume = self.tts_config.get("volume", 0.8)
            voice_id = self.tts_config.get("voice_id", 0)
            
            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.setProperty('volume', volume)
            
            # Get available voices
            voices = self.tts_engine.getProperty('voices')
            self.available_voices = []
            
            for i, voice in enumerate(voices):
                self.available_voices.append({
                    'id': i,
                    'name': voice.name,
                    'languages': voice.languages,
                    'gender': getattr(voice, 'gender', 'unknown')
                })
            
            # Set voice
            if voice_id < len(voices):
                self.tts_engine.setProperty('voice', voices[voice_id].id)
            
            self.logger.info(f"TTS initialized with {len(self.available_voices)} voices")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
    
    def _initialize_audio(self):
        """Initialize audio input/output."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Find audio device
            device_info = None
            if self.device_index is not None:
                device_info = self.pyaudio_instance.get_device_info_by_index(self.device_index)
            else:
                # Use default input device
                device_info = self.pyaudio_instance.get_default_input_device_info()
                self.device_index = device_info['index']
            
            self.logger.info(f"Using audio device: {device_info['name']}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audio: {e}")
    
    def start_listening(self, callback: Callable[[str], None] = None):
        """Start continuous speech recognition."""
        with self._lock:
            if self.is_listening:
                return
            
            if not self.vosk_model or not self.pyaudio_instance:
                self.logger.error("Speech recognition not properly initialized")
                return
            
            self.speech_callback = callback
            self.is_listening = True
            
            # Start audio stream
            try:
                self.audio_stream = self.pyaudio_instance.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._audio_stream_callback
                )
                
                self.audio_stream.start_stream()
                
                # Start processing thread
                self._listen_thread = threading.Thread(target=self._process_audio, daemon=True)
                self._listen_thread.start()
                
                self.logger.info("Started listening for speech")
                
            except Exception as e:
                self.logger.error(f"Failed to start audio stream: {e}")
                self.is_listening = False
    
    def stop_listening(self):
        """Stop speech recognition."""
        with self._lock:
            if not self.is_listening:
                return
            
            self.is_listening = False
            
            # Stop audio stream
            if self.audio_stream:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                    self.audio_stream = None
                except Exception as e:
                    self.logger.error(f"Error stopping audio stream: {e}")
            
            # Wait for processing thread
            if self._listen_thread and self._listen_thread.is_alive():
                self._listen_thread.join(timeout=1.0)
            
            self.logger.info("Stopped listening for speech")
    
    def _audio_stream_callback(self, in_data, frame_count, time_info, status):
        """Audio stream callback."""
        try:
            # Convert to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Add to queue for processing
            self._audio_queue.put(audio_data)
            
            # Call audio callback if set
            if self.audio_callback:
                self.audio_callback(audio_data)
            
            return (None, pyaudio.paContinue)
            
        except Exception as e:
            self.logger.error(f"Audio stream callback error: {e}")
            return (None, pyaudio.paAbort)
    
    def _process_audio(self):
        """Process audio data for speech recognition."""
        try:
            while self.is_listening:
                try:
                    # Get audio data with timeout
                    audio_data = self._audio_queue.get(timeout=0.1)
                    
                    # Convert to bytes for Vosk
                    audio_bytes = (audio_data * 32768).astype(np.int16).tobytes()
                    
                    # Process with Vosk
                    if self.recognizer.AcceptWaveform(audio_bytes):
                        # Complete utterance
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '').strip()
                        
                        if text and self.speech_callback:
                            self.speech_callback(text)
                    else:
                        # Partial result
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get('partial', '').strip()
                        
                        # Could emit partial results if needed
                        pass
                    
                    # Update audio processor
                    self.audio_processor.add_to_buffer(audio_data)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"Audio processing error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Audio processing thread error: {e}")
    
    def speak(self, text: str, blocking: bool = True):
        """Convert text to speech."""
        try:
            if not self.tts_engine:
                self.logger.error("TTS engine not initialized")
                return
            
            self.is_speaking = True
            
            if blocking:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self.is_speaking = False
            else:
                # Non-blocking speech
                def speak_async():
                    try:
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                    finally:
                        self.is_speaking = False
                
                threading.Thread(target=speak_async, daemon=True).start()
            
            self.logger.info(f"Speaking: {text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            self.is_speaking = False
    
    def set_voice(self, voice_id: int) -> bool:
        """Set TTS voice."""
        try:
            if not self.tts_engine:
                return False
            
            voices = self.tts_engine.getProperty('voices')
            if 0 <= voice_id < len(voices):
                self.tts_engine.setProperty('voice', voices[voice_id].id)
                self.logger.info(f"Voice changed to: {voices[voice_id].name}")
                return True
            else:
                self.logger.error(f"Invalid voice ID: {voice_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to set voice: {e}")
            return False
    
    def set_speech_rate(self, rate: int):
        """Set TTS speech rate."""
        try:
            if self.tts_engine:
                self.tts_engine.setProperty('rate', rate)
                self.logger.info(f"Speech rate set to: {rate}")
        except Exception as e:
            self.logger.error(f"Failed to set speech rate: {e}")
    
    def set_volume(self, volume: float):
        """Set TTS volume (0.0 to 1.0)."""
        try:
            if self.tts_engine:
                volume = max(0.0, min(1.0, volume))
                self.tts_engine.setProperty('volume', volume)
                self.logger.info(f"Volume set to: {volume}")
        except Exception as e:
            self.logger.error(f"Failed to set volume: {e}")
    
    def set_audio_callback(self, callback: Callable[[np.ndarray], None]):
        """Set callback for raw audio data."""
        self.audio_callback = callback
    
    def get_available_voices(self) -> list:
        """Get list of available TTS voices."""
        return self.available_voices.copy()
    
    def get_audio_devices(self) -> list:
        """Get list of available audio input devices."""
        devices = []
        
        try:
            if self.pyaudio_instance:
                for i in range(self.pyaudio_instance.get_device_count()):
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        devices.append({
                            'index': i,
                            'name': device_info['name'],
                            'channels': device_info['maxInputChannels'],
                            'sample_rate': device_info['defaultSampleRate']
                        })
        except Exception as e:
            self.logger.error(f"Failed to get audio devices: {e}")
        
        return devices
    
    def set_audio_device(self, device_index: int) -> bool:
        """Set audio input device."""
        try:
            if self.pyaudio_instance:
                device_info = self.pyaudio_instance.get_device_info_by_index(device_index)
                if device_info['maxInputChannels'] > 0:
                    self.device_index = device_index
                    self.logger.info(f"Audio device set to: {device_info['name']}")
                    
                    # Restart listening if active
                    if self.is_listening:
                        callback = self.speech_callback
                        self.stop_listening()
                        time.sleep(0.1)
                        self.start_listening(callback)
                    
                    return True
        except Exception as e:
            self.logger.error(f"Failed to set audio device: {e}")
        
        return False
    
    def get_status(self) -> dict:
        """Get engine status."""
        return {
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
            "vosk_initialized": self.vosk_model is not None,
            "tts_initialized": self.tts_engine is not None,
            "audio_initialized": self.pyaudio_instance is not None,
            "current_device": self.device_index,
            "available_voices": len(self.available_voices),
            "sample_rate": self.sample_rate,
            "chunk_size": self.chunk_size
        }
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_listening()
        
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except:
                pass
        
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
        
        self.logger.info("Speech engine cleaned up")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.cleanup()
