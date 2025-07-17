
# Advanced Voice Assistant

A comprehensive offline Python voice assistant with real-time speech processing, local LLM integration, advanced memory capabilities, and computer use functionality.

## Features

### 🎤 Real-time Speech Processing
- **Vosk-based Speech Recognition**: Offline speech-to-text with streaming audio
- **Multiple TTS Voices**: pyttsx3 with voice selection and customization
- **Voice Activity Detection**: Intelligent wake word detection and conversation management
- **Audio Visualization**: Real-time transparent blob that responds to speech syllables

### 🧠 Advanced AI Integration
- **Local LLM Support**: Ollama and LMStudio integration for offline AI processing
- **Natural Language Processing**: spaCy-powered intent recognition and entity extraction
- **Long-term Memory**: ChromaDB vector database for conversation history and learning
- **Context-aware Responses**: Semantic search and memory consolidation

### 💻 Computer Use Capabilities
- **Three Safety Levels**: Off, Safer, and God mode with configurable permissions
- **File Operations**: Safe file reading, writing, and management
- **System Information**: CPU, memory, disk usage monitoring
- **Process Control**: Running process information and management

### 🎨 Audio Visualization
- **Real-time Blob Animation**: OpenGL/Pygame-based transparent visualization
- **Syllable Synchronization**: Visual feedback that moves with speech patterns
- **Customizable Appearance**: Configurable colors, size, and animation speed
- **Status Indicators**: Visual feedback for listening and speaking states

### 🔧 Modular Architecture
- **Plugin System**: Extensible architecture for adding new capabilities
- **Configuration Management**: JSON-based configuration with hot reloading
- **Error Recovery**: Robust error handling and graceful degradation
- **Thread Safety**: Concurrent processing with proper synchronization

## Installation

### Prerequisites

- Python 3.8 or higher
- Linux (tested on Ubuntu 24.04/Linux Mint 22)
- Audio input device (microphone)
- At least 4GB RAM (8GB recommended)
- 10GB free disk space for models

### Quick Setup

1. **Clone and setup the project:**
   ```bash
   cd voice_assistant
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Start Ollama (in a separate terminal):**
   ```bash
   ollama serve
   ```

4. **Run the voice assistant:**
   ```bash
   python src/voice_assistant.py
   ```

### Manual Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download spaCy model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Download Vosk speech model:**
   ```bash
   mkdir -p models/vosk
   cd models/vosk
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   mv vosk-model-small-en-us-0.15 vosk-model-en
   ```

4. **Install and setup Ollama:**
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama2:7b
   ```

## Configuration

### Main Configuration (`configs/config.json`)

```json
{
  "audio": {
    "sample_rate": 16000,
    "wake_word": "assistant",
    "energy_threshold": 300
  },
  "llm": {
    "backend": "ollama",
    "model": "llama2:7b",
    "temperature": 0.7
  },
  "computer_use": {
    "safety_level": "safer",
    "require_confirmation": true
  },
  "visualization": {
    "enabled": true,
    "blob_color": [0, 255, 255, 128]
  }
}
```

### Safety Configuration (`configs/safety_rules.json`)

Configure computer use safety levels:
- **off**: No computer use capabilities
- **safer**: Limited safe operations (file reading, system info)
- **god**: Full system access (use with extreme caution)

## Usage

### Basic Commands

- **Wake up**: Say "assistant" to start a conversation
- **Math**: "Calculate 2 plus 2" or "What's the square root of 16?"
- **Time**: "What time is it?" or "What's today's date?"
- **System**: "Show memory usage" or "CPU status"
- **Files**: "List files in documents" or "Show current directory"
- **Help**: "What can you do?" or "Help me"

### Advanced Features

#### Memory System
The assistant remembers conversations and learns from interactions:
```python
# Conversations are automatically stored with vector embeddings
# Similar conversations are retrieved for context
# User preferences are learned over time
```

#### Computer Use
Enable computer automation with safety controls:
```bash
# Set safety level
python src/voice_assistant.py --safety-level safer

# Computer operations require confirmation in safer mode
# God mode allows full system access (dangerous!)
```

#### Audio Visualization
Real-time visual feedback:
- **Blue blob**: Listening state
- **Pulsing**: Speaking or processing
- **Color changes**: Different states and activities

## Architecture

### Core Components

1. **SpeechEngine**: Handles STT/TTS with Vosk and pyttsx3
2. **NLPProcessor**: Intent recognition and entity extraction with spaCy
3. **MemoryManager**: Long-term memory with ChromaDB vector database
4. **LLMBackend**: Local AI processing with Ollama/LMStudio
5. **ComputerController**: Safe computer automation with three-tier safety
6. **AudioVisualizer**: Real-time blob visualization with pygame

### Plugin System

Extend functionality with custom plugins:
```python
class CustomPlugin:
    def can_handle(self, text: str) -> bool:
        return "custom" in text.lower()
    
    def process(self, text: str, context: dict) -> dict:
        return {"response": "Custom response", "success": True}
```

### Memory Architecture

- **Conversations**: Vector embeddings for semantic search
- **Preferences**: User behavior learning and adaptation
- **Context**: Relevant information retrieval for responses

## Safety and Security

### Computer Use Safety

- **Three-tier system**: Progressive permission levels
- **Command validation**: Blocked dangerous commands
- **Path restrictions**: Limited file system access
- **User confirmation**: Required for sensitive operations
- **Action logging**: Complete audit trail

### Privacy

- **100% Offline**: No external API calls required
- **Local Processing**: All AI processing happens locally
- **Data Control**: Complete control over conversation data
- **No Telemetry**: No usage data sent anywhere

## Troubleshooting

### Common Issues

1. **Audio not working**:
   ```bash
   # Check audio devices
   python -c "import pyaudio; p=pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"
   ```

2. **Vosk model not found**:
   ```bash
   # Download and extract model
   cd models/vosk
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   mv vosk-model-small-en-us-0.15 vosk-model-en
   ```

3. **Ollama connection failed**:
   ```bash
   # Start Ollama server
   ollama serve
   
   # Check if model is available
   ollama list
   ```

4. **Memory issues**:
   ```bash
   # Clear memory database
   rm -rf embeddings/
   mkdir embeddings
   ```

### Performance Optimization

- **Reduce model size**: Use smaller Vosk/Ollama models
- **Disable visualization**: Use `--no-visualizer` flag
- **Adjust chunk size**: Modify `chunk_size` in config
- **Memory cleanup**: Regular memory database maintenance

## Development

### Adding New Features

1. **Create a plugin** in `src/plugins/`
2. **Extend command handler** for new intents
3. **Add configuration options** in config files
4. **Update documentation** and examples

### Testing

```bash
# Run basic tests
python -m pytest tests/

# Test individual components
python -c "from src.core.speech_engine import SpeechEngine; print('Speech engine OK')"
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

This project is open source. See LICENSE file for details.

## Acknowledgments

- **Vosk**: Offline speech recognition
- **spaCy**: Natural language processing
- **ChromaDB**: Vector database for memory
- **Ollama**: Local LLM serving
- **pygame**: Audio visualization
- **pyttsx3**: Text-to-speech synthesis

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review configuration files
3. Check logs for error messages
4. Create an issue with detailed information

---

**Note**: This is an advanced system requiring proper setup and configuration. Please read the safety documentation before enabling computer use features.
