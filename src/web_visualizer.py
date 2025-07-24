"""
Web-based Audio Visualizer
A browser-based visualization that can work in any environment.
"""

import json
import threading
import time
import logging
import math
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import deque
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import webbrowser
import os

from utils.config_loader import ConfigLoader


class WebVisualizerHandler(BaseHTTPRequestHandler):
    """HTTP handler for the web visualizer."""
    
    def __init__(self, visualizer_instance, *args, **kwargs):
        self.visualizer = visualizer_instance
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.serve_html()
        elif self.path == '/data':
            self.serve_data()
        elif self.path.endswith('.js'):
            self.serve_js()
        elif self.path.endswith('.css'):
            self.serve_css()
        else:
            self.send_error(404)
    
    def serve_html(self):
        """Serve the main HTML page."""
        html_content = self.visualizer.get_html_content()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_data(self):
        """Serve visualization data as JSON."""
        data = self.visualizer.get_visualization_data()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def serve_js(self):
        """Serve JavaScript files."""
        js_content = self.visualizer.get_js_content()
        self.send_response(200)
        self.send_header('Content-type', 'application/javascript')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(js_content.encode())
    
    def serve_css(self):
        """Serve CSS files."""
        css_content = self.visualizer.get_css_content()
        self.send_response(200)
        self.send_header('Content-type', 'text/css')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(css_content.encode())
    
    def log_message(self, format, *args):
        """Override to reduce logging noise."""
        pass


class WebAudioVisualizer:
    """Web-based audio visualizer using HTML5 Canvas."""
    
    def __init__(self, config_path: str = "configs/config.json", port: int = 12000):
        self.config = ConfigLoader(config_path).get_config()
        self.viz_config = self.config.get("visualization", {})
        self.port = port
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Visualization settings
        self.enabled = self.viz_config.get("enabled", True)
        self.window_size = tuple(self.viz_config.get("window_size", [400, 400]))
        self.blob_color = self.viz_config.get("blob_color", [0, 255, 255, 128])
        self.background_color = self.viz_config.get("background_color", [0, 0, 0, 0])
        self.animation_speed = self.viz_config.get("animation_speed", 0.1)
        
        # Audio data
        self.audio_buffer = deque(maxlen=1024)
        self.volume_history = deque(maxlen=60)  # 1 second at 60 FPS
        self.current_volume = 0.0
        self.peak_volume = 0.0
        
        # Animation state
        self.is_speaking = False
        self.is_listening = False
        self.animation_phase = 0.0
        self.syllable_pulses = deque(maxlen=10)
        self.start_time = time.time()
        
        # Server
        self.server = None
        self.server_thread = None
        self.running = False
        
        # Thread management
        self._lock = threading.RLock()
    
    def start(self):
        """Start the web visualizer server."""
        if not self.enabled:
            return
        
        with self._lock:
            if self.running:
                return
            
            try:
                # Create server with custom handler
                handler = lambda *args, **kwargs: WebVisualizerHandler(self, *args, **kwargs)
                self.server = HTTPServer(('0.0.0.0', self.port), handler)
                
                self.running = True
                self.server_thread = threading.Thread(target=self._run_server, daemon=True)
                self.server_thread.start()
                
                self.logger.info(f"Web visualizer started on port {self.port}")
                self.logger.info(f"Access at: http://localhost:{self.port}")
                
                # Try to open browser (optional)
                try:
                    webbrowser.open(f'http://localhost:{self.port}')
                except:
                    pass  # Browser opening is optional
                
            except Exception as e:
                self.logger.error(f"Failed to start web visualizer: {e}")
                self.enabled = False
    
    def stop(self):
        """Stop the web visualizer server."""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=1.0)
            
            self.logger.info("Web visualizer stopped")
    
    def _run_server(self):
        """Run the HTTP server."""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we're supposed to be running
                self.logger.error(f"Server error: {e}")
    
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
    
    def get_visualization_data(self) -> Dict[str, Any]:
        """Get current visualization data for the web client."""
        current_time = time.time()
        
        # Update animation phase
        self.animation_phase = (current_time - self.start_time) * self.animation_speed
        
        # Calculate pulse effects
        active_pulses = []
        while self.syllable_pulses and current_time - self.syllable_pulses[0]['time'] > 1.0:
            self.syllable_pulses.popleft()
        
        for pulse in self.syllable_pulses:
            age = current_time - pulse['time']
            if age < pulse['duration']:
                intensity = pulse['intensity'] * math.exp(-age * 3)
                active_pulses.append({
                    'age': age,
                    'intensity': intensity,
                    'duration': pulse['duration']
                })
        
        return {
            'timestamp': current_time,
            'animation_phase': self.animation_phase,
            'current_volume': self.current_volume,
            'peak_volume': self.peak_volume,
            'is_speaking': self.is_speaking,
            'is_listening': self.is_listening,
            'active_pulses': active_pulses,
            'volume_history': list(self.volume_history)[-20:],  # Last 20 samples
            'config': {
                'window_size': self.window_size,
                'blob_color': self.blob_color,
                'background_color': self.background_color,
                'animation_speed': self.animation_speed
            }
        }
    
    def get_html_content(self) -> str:
        """Get the HTML content for the visualizer."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIDA Voice Assistant Visualizer</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: Arial, sans-serif;
            overflow: hidden;
        }
        
        #visualizer {
            border: 1px solid #333;
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.8);
        }
        
        #controls {
            position: absolute;
            top: 10px;
            left: 10px;
            color: white;
            font-size: 12px;
            z-index: 100;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .speaking { background: #ff6464; }
        .listening { background: #64ff64; }
        .inactive { background: #666; }
        
        #volume-bar {
            position: absolute;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            width: 200px;
            height: 4px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 2px;
        }
        
        #volume-fill {
            height: 100%;
            background: linear-gradient(90deg, #64c8ff, #64ffff);
            border-radius: 2px;
            width: 0%;
            transition: width 0.1s ease;
        }
    </style>
</head>
<body>
    <div id="controls">
        <div>
            <span class="status-indicator speaking" id="speaking-indicator"></span>
            Speaking
        </div>
        <div>
            <span class="status-indicator listening" id="listening-indicator"></span>
            Listening
        </div>
        <div id="volume-text">Volume: 0%</div>
    </div>
    
    <canvas id="visualizer" width="400" height="400"></canvas>
    
    <div id="volume-bar">
        <div id="volume-fill"></div>
    </div>

    <script>
        class AudioVisualizer {
            constructor(canvas) {
                this.canvas = canvas;
                this.ctx = canvas.getContext('2d');
                this.data = null;
                this.blobPoints = [];
                this.numPoints = 16;
                this.baseRadius = Math.min(canvas.width, canvas.height) / 6;
                
                this.initializeBlobPoints();
                this.startAnimation();
                this.startDataFetch();
            }
            
            initializeBlobPoints() {
                this.blobPoints = [];
                for (let i = 0; i < this.numPoints; i++) {
                    const angle = (2 * Math.PI * i) / this.numPoints;
                    this.blobPoints.push({
                        angle: angle,
                        baseDistance: this.baseRadius,
                        currentDistance: this.baseRadius,
                        noiseOffset: i * 0.5
                    });
                }
            }
            
            startDataFetch() {
                const fetchData = () => {
                    fetch('/data')
                        .then(response => response.json())
                        .then(data => {
                            this.data = data;
                            this.updateUI();
                        })
                        .catch(error => console.error('Error fetching data:', error));
                };
                
                fetchData();
                setInterval(fetchData, 50); // 20 FPS data updates
            }
            
            updateUI() {
                if (!this.data) return;
                
                // Update status indicators
                const speakingIndicator = document.getElementById('speaking-indicator');
                const listeningIndicator = document.getElementById('listening-indicator');
                const volumeText = document.getElementById('volume-text');
                const volumeFill = document.getElementById('volume-fill');
                
                speakingIndicator.className = `status-indicator ${this.data.is_speaking ? 'speaking' : 'inactive'}`;
                listeningIndicator.className = `status-indicator ${this.data.is_listening ? 'listening' : 'inactive'}`;
                
                const volumePercent = Math.round(this.data.current_volume * 100);
                volumeText.textContent = `Volume: ${volumePercent}%`;
                volumeFill.style.width = `${volumePercent}%`;
            }
            
            startAnimation() {
                const animate = () => {
                    this.render();
                    requestAnimationFrame(animate);
                };
                animate();
            }
            
            render() {
                if (!this.data) return;
                
                const ctx = this.ctx;
                const centerX = this.canvas.width / 2;
                const centerY = this.canvas.height / 2;
                
                // Clear canvas
                ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                
                // Calculate current radius
                let currentRadius = this.baseRadius;
                
                if (this.data.is_speaking || this.data.is_listening) {
                    // Breathing effect
                    const breathing = 1.0 + 0.2 * Math.sin(this.data.animation_phase * 2);
                    currentRadius *= breathing;
                    
                    // Volume-based scaling
                    if (this.data.current_volume > 0) {
                        const volumeScale = 1.0 + (this.data.current_volume * 0.5);
                        currentRadius *= volumeScale;
                    }
                }
                
                // Calculate pulse effect
                let pulseEffect = 0;
                for (const pulse of this.data.active_pulses) {
                    pulseEffect += pulse.intensity;
                }
                
                // Update blob points
                const points = [];
                for (let i = 0; i < this.blobPoints.length; i++) {
                    const point = this.blobPoints[i];
                    
                    // Organic noise
                    const noiseValue = this.perlinNoise(
                        point.noiseOffset + this.data.animation_phase * 0.02,
                        this.data.animation_phase * 0.5
                    );
                    
                    // Combine effects
                    const distanceModifier = 1.0 + (noiseValue * 0.3) + (pulseEffect * 0.5);
                    const distance = currentRadius * distanceModifier;
                    
                    const x = centerX + distance * Math.cos(point.angle);
                    const y = centerY + distance * Math.sin(point.angle);
                    points.push([x, y]);
                }
                
                // Draw blob
                this.drawBlob(points);
            }
            
            drawBlob(points) {
                if (points.length < 3) return;
                
                const ctx = this.ctx;
                const color = this.data.config.blob_color;
                
                // Create gradient
                const centerX = this.canvas.width / 2;
                const centerY = this.canvas.height / 2;
                const gradient = ctx.createRadialGradient(
                    centerX, centerY, 0,
                    centerX, centerY, this.baseRadius * 2
                );
                
                gradient.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3] / 255})`);
                gradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`);
                
                // Draw filled blob
                ctx.beginPath();
                ctx.moveTo(points[0][0], points[0][1]);
                
                for (let i = 1; i < points.length; i++) {
                    ctx.lineTo(points[i][0], points[i][1]);
                }
                
                ctx.closePath();
                ctx.fillStyle = gradient;
                ctx.fill();
                
                // Add glow effect
                ctx.shadowColor = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.5)`;
                ctx.shadowBlur = 20;
                ctx.fill();
                ctx.shadowBlur = 0;
            }
            
            perlinNoise(x, y) {
                // Simple noise function
                return (Math.sin(x * 2.3) * Math.cos(y * 1.7) + 
                       Math.sin(x * 1.1) * Math.cos(y * 2.9)) * 0.5;
            }
        }
        
        // Initialize visualizer when page loads
        window.addEventListener('load', () => {
            const canvas = document.getElementById('visualizer');
            new AudioVisualizer(canvas);
        });
    </script>
</body>
</html>
        """
    
    def get_js_content(self) -> str:
        """Get JavaScript content (if serving separately)."""
        return "// JavaScript content would go here if serving separately"
    
    def get_css_content(self) -> str:
        """Get CSS content (if serving separately)."""
        return "/* CSS content would go here if serving separately */"
    
    def get_stats(self) -> dict:
        """Get visualization statistics."""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "port": self.port,
            "current_volume": self.current_volume,
            "peak_volume": self.peak_volume,
            "is_speaking": self.is_speaking,
            "is_listening": self.is_listening,
            "active_pulses": len(self.syllable_pulses),
            "animation_phase": self.animation_phase
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()