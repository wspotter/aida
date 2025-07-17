#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/stacy/.Xauthority
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __NV_PRIME_RENDER_OFFLOAD=1
export __NV_PRIME_RENDER_OFFLOAD_PROVIDER=NVIDIA-G0
export __GLX_GL_VENDOR=NVIDIA

./start_assistant.sh

