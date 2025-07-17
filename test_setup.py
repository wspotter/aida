#!/usr/bin/env python3
"""
Test script to verify voice assistant setup and components.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test all core imports."""
    print("🧪 Testing imports...")
    
    try:
        from src.utils.config_loader import ConfigLoader
        print("✓ ConfigLoader")
        
        from src.utils.safety_utils import SafetyValidator
        print("✓ SafetyValidator")
        
        from src.utils.audio_utils import AudioProcessor
        print("✓ AudioProcessor")
        
        from src.core.nlp_processor import NLPProcessor
        print("✓ NLPProcessor")
        
        from src.core.command_handler import CommandHandler
        print("✓ CommandHandler")
        
        from src.memory_manager import MemoryManager
        print("✓ MemoryManager")
        
        from src.llm_backend import LLMBackend
        print("✓ LLMBackend")
        
        from src.computer_controller import ComputerController
        print("✓ ComputerController")
        
        from src.audio_visualizer import AudioVisualizer
        print("✓ AudioVisualizer")
        
        from src.plugins.math_plugin import MathPlugin
        print("✓ MathPlugin")
        
        from src.plugins.system_plugin import SystemPlugin
        print("✓ SystemPlugin")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")
    
    try:
        from src.utils.config_loader import ConfigLoader
        
        config = ConfigLoader("configs/config.json")
        config_data = config.get_config()
        
        required_sections = ["audio", "tts", "llm", "memory", "computer_use", "visualization"]
        
        for section in required_sections:
            if section in config_data:
                print(f"✓ {section} configuration found")
            else:
                print(f"⚠️  {section} configuration missing")
        
        print("✅ Configuration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_plugins():
    """Test plugin system."""
    print("\n🔌 Testing plugins...")
    
    try:
        from src.plugins.math_plugin import MathPlugin
        from src.plugins.system_plugin import SystemPlugin
        
        # Test math plugin
        math_plugin = MathPlugin()
        if math_plugin.can_handle("calculate 2 + 2"):
            print("✓ Math plugin working")
        
        # Test system plugin
        system_plugin = SystemPlugin()
        if system_plugin.can_handle("show memory usage"):
            print("✓ System plugin working")
        
        print("✅ Plugin tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Plugin test failed: {e}")
        return False

def test_file_structure():
    """Test file structure."""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "configs/config.json",
        "configs/models_config.json", 
        "configs/safety_rules.json",
        "knowledge/knowledge_base.json",
        "src/voice_assistant.py",
        "requirements.txt",
        "setup.sh",
        "README.md",
        "SAFETY.md"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    if all_exist:
        print("✅ All required files present!")
    else:
        print("⚠️  Some files are missing")
    
    return all_exist

def main():
    """Run all tests."""
    print("🎤 Advanced Voice Assistant - Setup Test")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_imports,
        test_config,
        test_plugins
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    if all(results):
        print("🎉 All tests passed! Voice assistant is ready to use.")
        print("\n🚀 Next steps:")
        print("1. Run: ./setup.sh (to install dependencies)")
        print("2. Run: ./start_assistant.sh (to start the assistant)")
        print("3. Say 'assistant' to wake it up!")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("Run ./setup.sh to install missing dependencies.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
