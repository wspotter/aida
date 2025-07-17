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
