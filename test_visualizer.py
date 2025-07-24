#!/usr/bin/env python3
"""
Test script for the AIDA audio visualizer.
This script demonstrates the visualizer functionality.
"""

import sys
import time
import numpy as np
import logging
from pathlib import Path

# Add src to path
sys.path.append('src')

from audio_visualizer import AudioVisualizerManager

def main():
    """Main test function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting AIDA Visualizer Test")
    
    try:
        # Initialize visualizer manager
        logger.info("Initializing visualizer manager...")
        manager = AudioVisualizerManager()
        
        # Start the visualizer
        logger.info("Starting visualizer...")
        manager.start()
        
        # Get initial stats
        stats = manager.get_stats()
        logger.info(f"Visualizer stats: {stats}")
        
        if stats['current_visualizer'] == 'web':
            port = stats['active_stats']['port']
            logger.info(f"Web visualizer is running on port {port}")
            logger.info(f"Open your browser to: http://localhost:{port}")
            logger.info("You can also access it via the provided runtime URLs:")
            logger.info(f"  - https://work-1-wpolwhvcyfvwmotw.prod-runtime.all-hands.dev (if port is 12000)")
            logger.info(f"  - https://work-2-wpolwhvcyfvwmotw.prod-runtime.all-hands.dev (if port is 12001)")
        
        # Simulate audio activity
        logger.info("Simulating audio activity...")
        
        # Test different states
        test_scenarios = [
            ("Idle state", False, False, 0.0),
            ("Listening state", False, True, 0.2),
            ("Speaking state", True, False, 0.6),
            ("Active conversation", True, True, 0.8),
        ]
        
        for scenario_name, speaking, listening, base_volume in test_scenarios:
            logger.info(f"Testing: {scenario_name}")
            
            manager.set_speaking_state(speaking)
            manager.set_listening_state(listening)
            
            # Simulate audio data for 5 seconds
            for i in range(50):  # 5 seconds at 10 FPS
                # Generate synthetic audio data
                t = i * 0.1
                volume_variation = base_volume + 0.3 * np.sin(t * 2) * np.random.random()
                audio_data = np.random.random(1024) * volume_variation
                
                # Add some syllable-like pulses
                if speaking and i % 10 == 0:  # Every second
                    audio_data += np.random.random(1024) * 0.5
                
                manager.update_audio_data(audio_data)
                time.sleep(0.1)  # 10 FPS
            
            logger.info(f"Completed: {scenario_name}")
        
        # Keep running for a bit to allow manual testing
        logger.info("Visualizer is running. Press Ctrl+C to stop.")
        logger.info("You can interact with the web interface while this is running.")
        
        try:
            while True:
                # Generate some ambient audio activity
                audio_data = np.random.random(1024) * 0.1
                manager.update_audio_data(audio_data)
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Stopping visualizer...")
    
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        try:
            manager.stop()
            logger.info("Visualizer stopped successfully")
        except:
            pass

if __name__ == "__main__":
    main()