#!/bin/bash
# AIDA Voice Assistant Setup Script for Kubuntu
# This script handles system dependencies and Python package installation

set -e  # Exit on any error

echo "🚀 Setting up AIDA Voice Assistant on Kubuntu..."

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

# Check if running on Ubuntu/Kubuntu
if ! command -v apt &> /dev/null; then
    print_error "This script is designed for Ubuntu/Kubuntu systems with apt package manager"
    exit 1
fi

# Update package list
print_status "Updating package list..."
sudo apt update

# Install system dependencies
print_status "Installing system dependencies..."

# Audio dependencies
print_status "Installing audio system dependencies..."
sudo apt install -y \
    portaudio19-dev \
    python3-pyaudio \
    libasound2-dev \
    libpulse-dev \
    alsa-utils \
    pulseaudio

# SDL dependencies for pygame
print_status "Installing SDL dependencies for pygame..."
sudo apt install -y \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    libportmidi-dev

# Python development dependencies
print_status "Installing Python development dependencies..."
sudo apt install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    build-essential \
    cmake \
    pkg-config

# Optional: Install system Python packages that are often problematic
print_status "Installing system Python packages..."
sudo apt install -y \
    python3-numpy \
    python3-scipy \
    python3-matplotlib \
    python3-pygame

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_status "Detected Python version: $PYTHON_VERSION"

if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l) -eq 1 ]]; then
    print_warning "Python 3.8+ is recommended. You have $PYTHON_VERSION"
fi

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies with flexible versions
print_status "Installing Python dependencies..."

# Try the flexible requirements first
if [ -f "requirements-flexible.txt" ]; then
    print_status "Using flexible requirements..."
    pip install -r requirements-flexible.txt
elif [ -f "pyproject.toml" ]; then
    print_status "Using pyproject.toml..."
    pip install -e .
elif [ -f "requirements.txt" ]; then
    print_warning "Using original requirements.txt (may cause conflicts)..."
    pip install -r requirements.txt
else
    print_error "No requirements file found!"
    exit 1
fi

# Install additional packages that might be missing
print_status "Installing additional packages..."
pip install --upgrade \
    numpy \
    pygame \
    matplotlib

# Test the installation
print_status "Testing installation..."
python3 -c "
import sys
sys.path.append('src')

try:
    import numpy
    print('✅ numpy:', numpy.__version__)
except ImportError as e:
    print('❌ numpy import failed:', e)

try:
    import pygame
    print('✅ pygame:', pygame.version.ver)
except ImportError as e:
    print('❌ pygame import failed:', e)

try:
    import matplotlib
    print('✅ matplotlib:', matplotlib.__version__)
except ImportError as e:
    print('❌ matplotlib import failed:', e)

try:
    from audio_visualizer import AudioVisualizerManager
    print('✅ AIDA visualizer imports successfully')
except ImportError as e:
    print('❌ AIDA visualizer import failed:', e)
"

# Create activation script
print_status "Creating activation script..."
cat > activate_aida.sh << 'EOF'
#!/bin/bash
# Activate AIDA environment
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
echo "🎤 AIDA Voice Assistant environment activated"
echo "Run: python test_visualizer.py to test the visualizer"
echo "Run: python src/voice_assistant.py to start the assistant"
EOF

chmod +x activate_aida.sh

print_success "Setup completed successfully!"
print_status "To activate the environment, run: source activate_aida.sh"
print_status "To test the visualizer, run: python test_visualizer.py"

# Optional: Test the visualizer
read -p "Would you like to test the visualizer now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Testing visualizer..."
    python test_visualizer.py &
    VISUALIZER_PID=$!
    
    print_success "Visualizer started! Check your browser at:"
    print_success "http://localhost:12000"
    
    read -p "Press Enter to stop the visualizer..." -r
    kill $VISUALIZER_PID 2>/dev/null || true
fi

print_success "🎉 AIDA Voice Assistant is ready to use!"