# AIDA Dependency Troubleshooting Guide

## Common Version Conflicts on Kubuntu

### The Problem
The original `requirements.txt` uses pinned versions that often conflict with:
- System packages installed via apt
- Other Python packages with different version requirements
- Newer Python versions

### Solutions Provided

## 1. Flexible Requirements (`requirements-flexible.txt`)
Uses version ranges instead of pinned versions:
```bash
# Instead of numpy==1.24.3
numpy>=1.24.0  # Allows newer versions

# Instead of spacy==3.7.2  
spacy>=3.7.0,<4.0.0  # Allows patch updates, prevents major version conflicts
```

## 2. Modern Python Packaging (`pyproject.toml`)
- Uses modern Python packaging standards
- Better dependency resolution
- Optional dependency groups
- Development tools configuration

## 3. System Setup Script (`setup_kubuntu.sh`)
Handles Kubuntu-specific issues:
- Installs system dependencies via apt
- Creates isolated virtual environment
- Handles audio system dependencies
- Tests installation

## Quick Fix Commands

### Option 1: Use Flexible Requirements
```bash
# Create fresh virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with flexible versions
pip install -r requirements-flexible.txt
```

### Option 2: Use Modern Packaging
```bash
# Install in development mode
pip install -e .

# Or install with optional dependencies
pip install -e ".[dev,audio]"
```

### Option 3: Run Full Setup Script
```bash
./setup_kubuntu.sh
```

## Common Specific Conflicts

### NumPy Version Issues
**Problem**: `numpy==1.24.3` conflicts with newer packages expecting numpy 2.x

**Solution**:
```bash
pip install "numpy>=1.24.0"  # Allow newer versions
```

### PyGame SDL Issues
**Problem**: pygame fails to install due to missing SDL libraries

**Solution**:
```bash
sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev
pip install pygame
```

### PyAudio PortAudio Issues
**Problem**: pyaudio fails to compile due to missing PortAudio

**Solution**:
```bash
sudo apt install portaudio19-dev python3-pyaudio
pip install pyaudio
```

### ChromaDB/SQLite Issues
**Problem**: chromadb version conflicts with sqlite3

**Solution**:
```bash
pip install "chromadb>=0.4.0,<1.0.0"
```

## Environment Isolation

### Virtual Environment (Recommended)
```bash
python3 -m venv aida_env
source aida_env/bin/activate
pip install -r requirements-flexible.txt
```

### Conda Alternative
```bash
conda create -n aida python=3.11
conda activate aida
pip install -r requirements-flexible.txt
```

### Docker (Ultimate Isolation)
```dockerfile
FROM ubuntu:22.04
RUN apt update && apt install -y python3 python3-pip portaudio19-dev
COPY requirements-flexible.txt .
RUN pip install -r requirements-flexible.txt
```

## Debugging Version Conflicts

### Check Installed Versions
```bash
pip list | grep -E "(numpy|pygame|spacy|chromadb)"
```

### Find Conflicting Dependencies
```bash
pip check
```

### Show Dependency Tree
```bash
pip install pipdeptree
pipdeptree
```

### Force Reinstall Problematic Package
```bash
pip uninstall numpy
pip install --no-cache-dir "numpy>=1.24.0"
```

## System-Specific Kubuntu Issues

### Audio System Setup
```bash
# Ensure audio system is working
sudo apt install pulseaudio alsa-utils
pulseaudio --check -v

# Test audio devices
python3 -c "import pyaudio; p=pyaudio.PyAudio(); print([p.get_device_info_by_index(i) for i in range(p.get_device_count())])"
```

### Display Issues (for pygame)
```bash
# For headless systems
export SDL_VIDEODRIVER=dummy

# For X11 forwarding
export DISPLAY=:0
```

### Permission Issues
```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Logout and login again, or:
newgrp audio
```

## Testing Your Installation

### Quick Test
```bash
python3 -c "
import numpy, pygame, matplotlib
from src.audio_visualizer import AudioVisualizerManager
print('✅ All imports successful')
"
```

### Full Test
```bash
python test_visualizer.py
```

## If All Else Fails

### Nuclear Option - Fresh Environment
```bash
# Remove everything
rm -rf venv/
pip freeze | xargs pip uninstall -y

# Start fresh
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-flexible.txt
```

### Use System Packages
```bash
# Install via apt instead of pip
sudo apt install python3-numpy python3-pygame python3-matplotlib
pip install --no-deps -r requirements-flexible.txt
```

### Report Issues
If you're still having problems:
1. Run `pip check` and share the output
2. Share your Python version: `python3 --version`
3. Share your OS version: `lsb_release -a`
4. Share the full error message

## Prevention

### Best Practices
1. Always use virtual environments
2. Use version ranges, not pinned versions
3. Keep requirements files updated
4. Test on clean environments
5. Document system dependencies

### Maintenance
```bash
# Regularly update dependencies
pip list --outdated
pip install --upgrade package_name

# Update requirements
pip freeze > requirements-current.txt
```

The flexible requirements and setup script should resolve most version conflicts on Kubuntu!