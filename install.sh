#!/usr/bin/env bash
# Linux / macOS Automated Installer for Notes Workstation
# Sets up virtual environment, installs dependencies, and creates a desktop menu entry.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  Notes Workstation — University Knowledge Ecosystem      "
echo "  Linux / macOS Installer                                 "
echo "=========================================================="

# 1. Check Python
echo -e "\n[1/4] Checking Python installation..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is required. Please install python3 via your package manager." >&2
    exit 1
fi
echo "Found Python: $($PYTHON_CMD --version)"

# 2. Setup Virtual Environment
echo -e "\n[2/4] Setting up Python virtual environment..."
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "Created virtual environment at $VENV_DIR"
else
    echo "Virtual environment already exists."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# 3. Install Python Dependencies
echo -e "\n[3/4] Installing application dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet
"$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "Dependencies successfully installed."

# 4. Make runners executable
chmod +x "$SCRIPT_DIR/run_desktop.sh"

# 5. Linux Desktop Entry (.desktop)
if [ "$(uname)" = "Linux" ]; then
    echo -e "\n[4/4] Creating Linux application menu entry..."
    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR"
    DESKTOP_FILE="$APPS_DIR/notes-workstation.desktop"
    
    cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Name=Notes Workstation
Comment=University Knowledge & Fact-Checking Workstation
Exec=$SCRIPT_DIR/run_desktop.sh
Icon=$SCRIPT_DIR/src-tauri/icons/128x128.png
Terminal=false
Type=Application
Categories=Office;Education;Science;
EOL
    chmod +x "$DESKTOP_FILE"
    echo "Desktop entry created at $DESKTOP_FILE"
fi

echo "=========================================================="
echo "  Installation Completed Successfully!                   "
echo "  Launch the application using './run_desktop.sh'        "
echo "=========================================================="
