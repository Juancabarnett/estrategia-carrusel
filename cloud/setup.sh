#!/usr/bin/env bash
# Setup script for the Claude Code cloud environment (Ubuntu). Paste it in the
# environment's "Setup script" field. It must exit 0 and finish in about 5 minutes.
set -u

# Video and audio processing.
apt-get update -y && apt-get install -y ffmpeg || true

# Python packages used by the pack scripts and by Earshot's sound effects bank.
pip install --quiet pillow numpy scipy soundfile soxr pyloudnorm librosa scikit-learn matplotlib || true

# Warm the HyperFrames CLI so the first render does not wait for npm.
npx --yes hyperframes@latest --version || true

# Earshot's listening tools (PyTorch CPU and about 1.2 GB of models) are optional.
# They need download.pytorch.org and huggingface.co in the allowed domains, so they
# are left out here. Install them by hand in a session if you need them:
#   pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install transformers

exit 0
