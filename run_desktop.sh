#!/usr/bin/env bash
# Launcher script for Notes Workstation Desktop (Linux / macOS)

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "[Notes Desktop] Starting application environment..."

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python desktop.py "$@"
elif [ -f "venv/bin/python" ]; then
    venv/bin/python desktop.py "$@"
else
    python3 desktop.py "$@"
fi
