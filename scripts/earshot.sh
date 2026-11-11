#!/usr/bin/env bash
# Linux/macOS twin of scripts/earshot.cmd: runs Earshot from the code in tools/earshot.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/tools/earshot${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONUTF8=1
exec python3 -m earshot.cli "$@"
