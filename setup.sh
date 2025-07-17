
#!/bin/bash

# Advanced Voice Assistant Setup Script
echo "🎤 Setting up Advanced Voice Assistant..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on supported system
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_warning "This setup script is designed for Linux. You may need to adapt it for your system."
fi

# Check Python version
print_status "Checking Python version..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
    required_version="3.8"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python 3.8+ required. Found: $python_version"
        exit 1
    fi
    print_success "Python $python_version found"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check for required system packages
print_status "Checking system dependencies..."
missing_packages=()

# Check for audio development libraries
if ! pkg-config --exists alsa; then
    missing_packages+=("libasound2-dev")
fi

if ! pkg-config --exists portaudio-2.0; then
    missing_packages+=("portaudio19-dev")
fi

# Check for other dependencies
for cmd in wget unzip curl; do
    if ! command -v $cmd &> /dev/null; then
        missing_packages+=($cmd)
    fi
done

if [ ${#missing_packages[@]} -ne 0 ]; then
    print_warning "Missing system packages: ${missing_packages[*]}"
    print_status "Installing missing packages..."
    sudo apt update
    sudo apt install -y "${missing_packages[@]}"
fi

# Create virtual environment
print_status "Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

python3.10 -m venv env

source /home/stacy/ai-stack/aida/env/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Download spaCy model
print_status "Downloading spaCy English model..."
python -m spacy download en_core_web_sm

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p models/vosk
mkdir -p embeddings
mkdir -p logs
mkdir -p knowledge

# Download Vosk model
print_status "Downloading Vosk speech recognition model..."
cd models/vosk

if [ ! -d "vosk-model-en" ]; then
    if [ ! -f "vosk-model-small-en-us-0.15.zip" ]; then
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    fi
    
    print_status "Extracting Vosk model..."
    unzip -q vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 vosk-model-en
    rm vosk-model-small-en-us-0.15.zip
    print_success "Vosk model installed"
else
    print_success "Vosk model already exists"
fi

cd ../..

# Check for Ollama installation
print_status "Checking for Ollama..."
if ! command -v ollama &> /dev/null; then
    print_status "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    print_success "Ollama installed"
else
    print_success "Ollama already installed"
fi

# Check if Ollama is running
print_status "Checking Ollama service..."
if ! pgrep -x "ollama" > /dev/null; then
    print_status "Starting Ollama service..."
    ollama serve &
    sleep 3
fi

# Pull recommended model
print_status "Pulling recommended Ollama model (this may take a while)..."
if ollama list | grep -q "llama2:7b"; then
    print_success "llama2:7b model already available"
else
    ollama pull llama2:7b
    print_success "llama2:7b model downloaded"
fi

# Set permissions
print_status "Setting permissions..."
chmod +x src/voice_assistant.py
find . -name "*.py" -exec chmod +r {} \;

# Create launcher script
print_status "Creating launcher script..."
cat > start_assistant.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

source /home/stacy/ai-stack/aida/env/bin/activate


# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Start the voice assistant
python src/voice_assistant.py "$@"
EOF

chmod +x start_assistant.sh

# Create systemd service file (optional)
print_status "Creating systemd service template..."
cat > voice-assistant.service << EOF
[Unit]
Description=Advanced Voice Assistant
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/src/voice_assistant.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_success "Setup complete!"
echo ""
echo "🚀 To start the voice assistant:"
echo "   ./start_assistant.sh"
echo ""
echo "📖 Or manually:"
echo "   1. source venv/bin/activate"
echo "   2. python src/voice_assistant.py"
echo ""
echo "⚙️  Configuration files are in configs/"
echo "📚 Read README.md for detailed usage instructions"
echo "🔒 Read SAFETY.md for computer use safety information"
echo ""
echo "🎯 Quick test:"
echo "   python -c \"from src.core.speech_engine import SpeechEngine; print('✓ Speech engine OK')\""
echo ""

# Test basic imports
print_status "Testing basic imports..."
source /home/stacy/ai-stack/aida/env/bin/activate
python -c "
try:
    from src.core.speech_engine import SpeechEngine
    from src.memory_manager import MemoryManager
    from src.llm_backend import LLMBackend
    print('✓ All core modules imported successfully')
except Exception as e:
    print(f'✗ Import error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "All components ready!"
else
    print_error "Some components failed to import. Check the error messages above."
fi
