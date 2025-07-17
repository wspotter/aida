"""
Audio Visualizer
Real-time transparent blob visualization that responds to speech syllables.
"""

import math
import threading
import time
import logging
from typing import Tuple, List, Optional
from datetime import datetime

import pygame
import numpy as np
from collections import deque

from  utils.config_loader import ConfigLoader


class AudioVisualizer:
    """Real-time audio visualization with transparent blob animation."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.viz_config = self.config.get("visualization", {})
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Visualization settings
        self.enabled = self.viz_config.get("enabled", True)
        self.window_size = tuple(self.viz_config.get("window_size", [400, 400]))
        self.blob_color = tuple(self.viz_config.get("blob_color", [0, 255, 255, 128]))
        self.background_color = tuple(self.viz_config.get("background_color", [0, 0, 0, 0]))
        self.animation_speed = self.viz_config.get("animation_speed", 0.1)
        
        # Pygame initialization
        self.screen = None
        self.clock = None
        self.running = False
        
        # Audio data
        self.audio_buffer = deque(maxlen=1024)
        self.volume_history = deque(maxlen=60)  # 1 second at 60 FPS
        self.current_volume = 0.0
        self.peak_volume = 0.0
        
        # Blob animation
        self.blob_center = (self.window_size[0] // 2, self.window_size[1] // 2)
        self.base_radius = min(self.window_size) // 6
        self.current_radius = self.base_radius
        self.blob_points = []
        self.num_points = 16
        self.noise_offset = 0.0
        
        # Animation state
        self.is_speaking = False
        self.is_listening = False
        self.animation_phase = 0.0
        self.syllable_pulses = deque(maxlen=10)
        
        # Thread management
        self._lock = threading.RLock()
        self._animation_thread = None
        
        if self.enabled:
            self._initialize_pygame()
    
    def _initialize_pygame(self):
        """Initialize pygame for visualization."""
        try:
            pygame.init()
            pygame.mixer.init()
            
            # Set up display with transparency support
            self.screen = pygame.display.set_mode(
                self.window_size, 
                pygame.SRCALPHA | pygame.NOFRAME
            )
            pygame.display.set_caption("Voice Assistant Visualizer")
            
            # Set window to be always on top and transparent
            self._setup_transparent_window()
            
            self.clock = pygame.time.Clock()
            
            # Generate initial blob points
            self._generate_blob_points()
            
            self.logger.info("Audio visualizer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pygame: {e}")
            self.enabled = False
    
    def _setup_transparent_window(self):
        """Set up transparent window properties."""
        try:
            # This is platform-specific and may need adjustment
            import os
            if os.name == 'posix':  # Linux/Unix
                # Try to set window properties for transparency
                pass  # Transparency handling varies by window manager
        except Exception as e:
            self.logger.warning(f"Could not set window transparency: {e}")
    
    def _generate_blob_points(self):
        """Generate points for the blob shape."""
        self.blob_points = []
        for i in range(self.num_points):
            angle = (2 * math.pi * i) / self.num_points
            self.blob_points.append({
                'angle': angle,
                'base_distance': self.base_radius,
                'current_distance': self.base_radius,
                'noise_offset': i * 0.5
            })
    
    def start(self):
        """Start the visualization."""
        if not self.enabled:
            return
        
        with self._lock:
            if self.running:
                return
            
            self.running = True
            self._animation_thread = threading.Thread(target=self._animation_loop, daemon=True)
            self._animation_thread.start()
            
            self.logger.info("Audio visualizer started")
    
    def stop(self):
        """Stop the visualization."""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            
            if self._animation_thread and self._animation_thread.is_alive():
                self._animation_thread.join(timeout=1.0)
            
            if self.screen:
                pygame.quit()
            
            self.logger.info("Audio visualizer stopped")
    
    def _animation_loop(self):
        """Main animation loop."""
        try:
            while self.running:
                # Handle pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                
                # Update animation
                self._update_animation()
                
                # Render frame
                self._render_frame()
                
                # Control frame rate
                self.clock.tick(60)  # 60 FPS
                
        except Exception as e:
            self.logger.error(f"Animation loop error: {e}")
        finally:
            self.running = False
    
    def _update_animation(self):
        """Update animation state."""
        current_time = time.time()
        
        # Update animation phase
        self.animation_phase += self.animation_speed
        if self.animation_phase > 2 * math.pi:
            self.animation_phase -= 2 * math.pi
        
        # Update noise offset for organic movement
        self.noise_offset += 0.02
        
        # Calculate target radius based on audio
        target_radius = self.base_radius
        
        if self.is_speaking or self.is_listening:
            # Breathing effect when active
            breathing = 1.0 + 0.2 * math.sin(self.animation_phase * 2)
            target_radius *= breathing
            
            # Volume-based scaling
            if self.current_volume > 0:
                volume_scale = 1.0 + (self.current_volume * 0.5)
                target_radius *= volume_scale
        
        # Smooth radius transition
        self.current_radius += (target_radius - self.current_radius) * 0.1
        
        # Update blob points
        for i, point in enumerate(self.blob_points):
            # Base organic movement
            noise_value = self._perlin_noise(
                point['noise_offset'] + self.noise_offset,
                self.animation_phase * 0.5
            )
            
            # Syllable pulse effect
            pulse_effect = self._calculate_pulse_effect(current_time)
            
            # Combine effects
            distance_modifier = 1.0 + (noise_value * 0.3) + pulse_effect
            point['current_distance'] = self.current_radius * distance_modifier
    
    def _calculate_pulse_effect(self, current_time: float) -> float:
        """Calculate the effect of syllable pulses."""
        total_effect = 0.0
        
        # Remove old pulses
        while self.syllable_pulses and current_time - self.syllable_pulses[0]['time'] > 1.0:
            self.syllable_pulses.popleft()
        
        # Calculate combined effect of active pulses
        for pulse in self.syllable_pulses:
            age = current_time - pulse['time']
            if age < pulse['duration']:
                # Exponential decay
                intensity = pulse['intensity'] * math.exp(-age * 3)
                total_effect += intensity
        
        return total_effect
    
    def _perlin_noise(self, x: float, y: float) -> float:
        """Simple Perlin noise implementation."""
        # Simplified noise function for organic blob movement
        return (math.sin(x * 2.3) * math.cos(y * 1.7) + 
                math.sin(x * 1.1) * math.cos(y * 2.9)) * 0.5
    
    def _render_frame(self):
        """Render a single frame."""
        try:
            # Clear screen with transparent background
            self.screen.fill(self.background_color)
            
            # Draw blob
            self._draw_blob()
            
            # Draw status indicators
            self._draw_status_indicators()
            
            # Update display
            pygame.display.flip()
            
        except Exception as e:
            self.logger.error(f"Render error: {e}")
    
    def _draw_blob(self):
        """Draw the animated blob."""
        if not self.blob_points:
            return
        
        # Calculate blob outline points
        outline_points = []
        for point in self.blob_points:
            x = self.blob_center[0] + point['current_distance'] * math.cos(point['angle'])
            y = self.blob_center[1] + point['current_distance'] * math.sin(point['angle'])
            outline_points.append((x, y))
        
        # Create surface for blob with alpha
        blob_surface = pygame.Surface(self.window_size, pygame.SRCALPHA)
        
        # Draw filled blob
        if len(outline_points) >= 3:
            pygame.draw.polygon(blob_surface, self.blob_color, outline_points)
        
        # Add glow effect
        self._add_glow_effect(blob_surface, outline_points)
        
        # Blit to main surface
        self.screen.blit(blob_surface, (0, 0))
    
    def _add_glow_effect(self, surface: pygame.Surface, points: List[Tuple[float, float]]):
        """Add glow effect around the blob."""
        if not points:
            return
        
        # Create multiple layers for glow
        glow_layers = 3
        for layer in range(glow_layers):
            glow_radius = (layer + 1) * 2
            glow_alpha = max(20 - layer * 5, 5)
            
            # Create glow color with reduced alpha
            glow_color = (*self.blob_color[:3], glow_alpha)
            
            # Draw glow layer
            for point in points:
                pygame.draw.circle(
                    surface, 
                    glow_color, 
                    (int(point[0]), int(point[1])), 
                    glow_radius
                )
    
    def _draw_status_indicators(self):
        """Draw status indicators."""
        indicator_size = 10
        margin = 15
        
        # Speaking indicator (top-left)
        if self.is_speaking:
            color = (255, 100, 100, 180)  # Red
            pygame.draw.circle(
                self.screen, 
                color, 
                (margin, margin), 
                indicator_size
            )
        
        # Listening indicator (top-right)
        if self.is_listening:
            color = (100, 255, 100, 180)  # Green
            pygame.draw.circle(
                self.screen, 
                color, 
                (self.window_size[0] - margin, margin), 
                indicator_size
            )
        
        # Volume indicator (bottom)
        if self.current_volume > 0:
            bar_width = int(self.window_size[0] * 0.6)
            bar_height = 4
            bar_x = (self.window_size[0] - bar_width) // 2
            bar_y = self.window_size[1] - margin
            
            # Background bar
            pygame.draw.rect(
                self.screen,
                (50, 50, 50, 100),
                (bar_x, bar_y, bar_width, bar_height)
            )
            
            # Volume bar
            volume_width = int(bar_width * min(self.current_volume, 1.0))
            if volume_width > 0:
                pygame.draw.rect(
                    self.screen,
                    (100, 200, 255, 150),
                    (bar_x, bar_y, volume_width, bar_height)
                )
    
    def update_audio_data(self, audio_data: np.ndarray):
        """Update audio data for visualization."""
        if not self.enabled:
            return
        
        try:
            # Calculate volume (RMS)
            if len(audio_data) > 0:
                rms = np.sqrt(np.mean(audio_data ** 2))
                self.current_volume = min(rms * 10, 1.0)  # Scale and clamp
                
                # Update peak volume
                if self.current_volume > self.peak_volume:
                    self.peak_volume = self.current_volume
                else:
                    self.peak_volume *= 0.95  # Decay
                
                # Add to history
                self.volume_history.append(self.current_volume)
                
                # Detect syllables (simple peak detection)
                if len(self.volume_history) >= 3:
                    recent_volumes = list(self.volume_history)[-3:]
                    if (recent_volumes[1] > recent_volumes[0] and 
                        recent_volumes[1] > recent_volumes[2] and
                        recent_volumes[1] > 0.3):
                        self.add_syllable_pulse(recent_volumes[1])
        
        except Exception as e:
            self.logger.error(f"Audio data update error: {e}")
    
    def add_syllable_pulse(self, intensity: float = 0.5):
        """Add a syllable pulse effect."""
        if not self.enabled:
            return
        
        pulse = {
            'time': time.time(),
            'intensity': intensity,
            'duration': 0.3  # 300ms pulse
        }
        
        self.syllable_pulses.append(pulse)
    
    def set_speaking_state(self, speaking: bool):
        """Set speaking state."""
        self.is_speaking = speaking
        if speaking:
            self.add_syllable_pulse(0.7)
    
    def set_listening_state(self, listening: bool):
        """Set listening state."""
        self.is_listening = listening
    
    def set_blob_color(self, color: Tuple[int, int, int, int]):
        """Set blob color (RGBA)."""
        self.blob_color = color
    
    def set_animation_speed(self, speed: float):
        """Set animation speed."""
        self.animation_speed = max(0.01, min(speed, 1.0))
    
    def resize_window(self, width: int, height: int):
        """Resize the visualization window."""
        if not self.enabled:
            return
        
        try:
            self.window_size = (width, height)
            self.blob_center = (width // 2, height // 2)
            self.base_radius = min(width, height) // 6
            
            if self.screen:
                self.screen = pygame.display.set_mode(
                    self.window_size, 
                    pygame.SRCALPHA | pygame.NOFRAME
                )
            
            self._generate_blob_points()
            
        except Exception as e:
            self.logger.error(f"Window resize error: {e}")
    
    def get_stats(self) -> dict:
        """Get visualization statistics."""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "window_size": self.window_size,
            "current_volume": self.current_volume,
            "peak_volume": self.peak_volume,
            "is_speaking": self.is_speaking,
            "is_listening": self.is_listening,
            "active_pulses": len(self.syllable_pulses),
            "animation_phase": self.animation_phase
        }
    
    def save_screenshot(self, filename: str) -> bool:
        """Save a screenshot of the current visualization."""
        if not self.enabled or not self.screen:
            return False
        
        try:
            pygame.image.save(self.screen, filename)
            self.logger.info(f"Screenshot saved: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Screenshot save error: {e}")
            return False
    
    def toggle_visibility(self):
        """Toggle visualization visibility."""
        if not self.enabled:
            return
        
        # This would hide/show the window
        # Implementation depends on the window manager
        pass
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()


class AudioVisualizerManager:
    """Manager for multiple visualization modes."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.logger = logging.getLogger(__name__)
        
        # Available visualizers
        self.visualizers = {
            "blob": AudioVisualizer(config_path),
            # Could add more visualizer types here
        }
        
        self.current_visualizer = "blob"
        self.active_visualizer = self.visualizers[self.current_visualizer]
    
    def start(self):
        """Start the active visualizer."""
        if self.active_visualizer:
            self.active_visualizer.start()
    
    def stop(self):
        """Stop all visualizers."""
        for visualizer in self.visualizers.values():
            visualizer.stop()
    
    def switch_visualizer(self, visualizer_type: str) -> bool:
        """Switch to a different visualizer type."""
        if visualizer_type not in self.visualizers:
            self.logger.error(f"Unknown visualizer type: {visualizer_type}")
            return False
        
        # Stop current visualizer
        if self.active_visualizer:
            self.active_visualizer.stop()
        
        # Switch to new visualizer
        self.current_visualizer = visualizer_type
        self.active_visualizer = self.visualizers[visualizer_type]
        self.active_visualizer.start()
        
        self.logger.info(f"Switched to visualizer: {visualizer_type}")
        return True
    
    def update_audio_data(self, audio_data: np.ndarray):
        """Update audio data for the active visualizer."""
        if self.active_visualizer:
            self.active_visualizer.update_audio_data(audio_data)
    
    def set_speaking_state(self, speaking: bool):
        """Set speaking state for the active visualizer."""
        if self.active_visualizer:
            self.active_visualizer.set_speaking_state(speaking)
    
    def set_listening_state(self, listening: bool):
        """Set listening state for the active visualizer."""
        if self.active_visualizer:
            self.active_visualizer.set_listening_state(listening)
    
    def get_stats(self) -> dict:
        """Get statistics for all visualizers."""
        return {
            "current_visualizer": self.current_visualizer,
            "available_visualizers": list(self.visualizers.keys()),
            "active_stats": self.active_visualizer.get_stats() if self.active_visualizer else None
        }
