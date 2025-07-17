
"""
Audio processing utilities.
"""

import numpy as np
import logging
from typing import Tuple, Optional
import threading
import time


class AudioProcessor:
    """Audio processing utilities for voice assistant."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Audio parameters
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        
        # Voice activity detection
        self.energy_threshold = 300
        self.silence_timeout = 3.0
        self.last_speech_time = 0
        
        # Audio buffers
        self.audio_buffer = []
        self.max_buffer_size = 16000 * 10  # 10 seconds
    
    def calculate_energy(self, audio_data: np.ndarray) -> float:
        """Calculate audio energy (RMS)."""
        try:
            if len(audio_data) == 0:
                return 0.0
            
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data ** 2))
            return energy * 1000  # Scale for easier threshold comparison
            
        except Exception as e:
            self.logger.error(f"Energy calculation failed: {e}")
            return 0.0
    
    def detect_voice_activity(self, audio_data: np.ndarray) -> bool:
        """Detect voice activity in audio data."""
        try:
            energy = self.calculate_energy(audio_data)
            
            if energy > self.energy_threshold:
                self.last_speech_time = time.time()
                return True
            
            # Check if we're still in speech based on timeout
            time_since_speech = time.time() - self.last_speech_time
            return time_since_speech < self.silence_timeout
            
        except Exception as e:
            self.logger.error(f"Voice activity detection failed: {e}")
            return False
    
    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio data."""
        try:
            if len(audio_data) == 0:
                return audio_data
            
            # Normalize to [-1, 1] range
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                return audio_data / max_val
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Audio normalization failed: {e}")
            return audio_data
    
    def apply_noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply simple noise reduction."""
        try:
            if len(audio_data) == 0:
                return audio_data
            
            # Simple high-pass filter to remove low-frequency noise
            # This is a basic implementation - could be improved with proper DSP
            filtered = audio_data.copy()
            
            # Apply simple moving average filter
            window_size = min(5, len(filtered))
            if window_size > 1:
                kernel = np.ones(window_size) / window_size
                filtered = np.convolve(filtered, kernel, mode='same')
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"Noise reduction failed: {e}")
            return audio_data
    
    def detect_syllables(self, audio_data: np.ndarray) -> int:
        """Detect number of syllables in audio data."""
        try:
            if len(audio_data) == 0:
                return 0
            
            # Simple syllable detection based on energy peaks
            energy = self.calculate_energy(audio_data)
            
            # Smooth the energy signal
            smoothed = np.convolve(audio_data ** 2, np.ones(100) / 100, mode='same')
            
            # Find peaks
            peaks = []
            threshold = np.mean(smoothed) * 1.5
            
            for i in range(1, len(smoothed) - 1):
                if (smoothed[i] > smoothed[i-1] and 
                    smoothed[i] > smoothed[i+1] and 
                    smoothed[i] > threshold):
                    peaks.append(i)
            
            # Filter peaks that are too close together
            filtered_peaks = []
            min_distance = self.sample_rate // 10  # 100ms minimum
            
            for peak in peaks:
                if not filtered_peaks or peak - filtered_peaks[-1] > min_distance:
                    filtered_peaks.append(peak)
            
            return len(filtered_peaks)
            
        except Exception as e:
            self.logger.error(f"Syllable detection failed: {e}")
            return 0
    
    def add_to_buffer(self, audio_data: np.ndarray):
        """Add audio data to buffer."""
        with self._lock:
            try:
                self.audio_buffer.extend(audio_data.tolist())
                
                # Keep buffer size manageable
                if len(self.audio_buffer) > self.max_buffer_size:
                    excess = len(self.audio_buffer) - self.max_buffer_size
                    self.audio_buffer = self.audio_buffer[excess:]
                    
            except Exception as e:
                self.logger.error(f"Buffer update failed: {e}")
    
    def get_buffer_data(self, duration_seconds: float = 1.0) -> np.ndarray:
        """Get recent audio data from buffer."""
        with self._lock:
            try:
                samples_needed = int(duration_seconds * self.sample_rate)
                
                if len(self.audio_buffer) >= samples_needed:
                    return np.array(self.audio_buffer[-samples_needed:])
                else:
                    return np.array(self.audio_buffer)
                    
            except Exception as e:
                self.logger.error(f"Buffer retrieval failed: {e}")
                return np.array([])
    
    def clear_buffer(self):
        """Clear audio buffer."""
        with self._lock:
            self.audio_buffer = []
    
    def set_energy_threshold(self, threshold: float):
        """Set voice activity detection threshold."""
        self.energy_threshold = max(0, threshold)
        self.logger.info(f"Energy threshold set to: {self.energy_threshold}")
    
    def get_audio_stats(self) -> dict:
        """Get audio processing statistics."""
        with self._lock:
            buffer_duration = len(self.audio_buffer) / self.sample_rate if self.audio_buffer else 0
            
            return {
                "sample_rate": self.sample_rate,
                "chunk_size": self.chunk_size,
                "channels": self.channels,
                "energy_threshold": self.energy_threshold,
                "buffer_size": len(self.audio_buffer),
                "buffer_duration": buffer_duration,
                "last_speech_time": self.last_speech_time
            }


def convert_audio_format(audio_data: np.ndarray, 
                        source_rate: int, 
                        target_rate: int) -> np.ndarray:
    """Convert audio sample rate."""
    try:
        if source_rate == target_rate:
            return audio_data
        
        # Simple resampling (linear interpolation)
        # For production, use scipy.signal.resample for better quality
        ratio = target_rate / source_rate
        new_length = int(len(audio_data) * ratio)
        
        if new_length == 0:
            return np.array([])
        
        # Linear interpolation
        old_indices = np.linspace(0, len(audio_data) - 1, new_length)
        new_audio = np.interp(old_indices, np.arange(len(audio_data)), audio_data)
        
        return new_audio
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Audio format conversion failed: {e}")
        return audio_data


def apply_gain(audio_data: np.ndarray, gain_db: float) -> np.ndarray:
    """Apply gain to audio data."""
    try:
        if gain_db == 0:
            return audio_data
        
        # Convert dB to linear scale
        gain_linear = 10 ** (gain_db / 20)
        
        # Apply gain and clip to prevent overflow
        gained_audio = audio_data * gain_linear
        return np.clip(gained_audio, -1.0, 1.0)
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Gain application failed: {e}")
        return audio_data
