#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Ensure Homebrew paths are visible when double-clicked from macOS Finder
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/local/bin:$PATH"

echo "=== genvault v2 setup (macOS / Linux) ==="
echo

pause_if_gui() {
  if [ -t 0 ]; then
    echo
    read -r -p "Press Enter to close..." _ || true
  fi
}

# --- find Python >= 3.10 ---
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
      PY="$cand"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "ERROR: Python 3.10 or newer not found."
  if [ "$(uname -s)" = "Darwin" ]; then
    echo "Install it via Homebrew:  brew install python@3.12"
    echo "or download from https://www.python.org/downloads/"
  else
    echo "Install python3 (>= 3.10) and python3-venv via your package manager."
  fi
  pause_if_gui
  exit 1
fi
echo "Using Python: $("$PY" --version)"

# --- check ffmpeg / ffprobe ---
FF_OK=1
command -v ffmpeg >/dev/null 2>&1 || FF_OK=0
command -v ffprobe >/dev/null 2>&1 || FF_OK=0
if [ "$FF_OK" = "0" ]; then
  echo
  echo "WARNING: ffmpeg / ffprobe not found on PATH."
  echo "         Thumbnails, video metadata and rendering need them."
  if [ "$(uname -s)" = "Darwin" ]; then
    echo "         Install via Homebrew:  brew install ffmpeg"
  else
    echo "         Install via your package manager (e.g. sudo apt install ffmpeg)."
  fi
  echo
fi

# --- virtualenv + dependencies ---
if [ ! -x ".venv/bin/python" ]; then
  echo "Creating virtual environment (.venv)..."
  "$PY" -m venv .venv
fi
echo "Installing Python packages (first run takes 1-2 minutes)..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet

# --- library folder + port ---
echo
DEFAULT_LIB="$HOME/genvault"
echo "Where should genvault store your library (all media, thumbnails, database)?"
echo "Pick a drive/folder with enough free space."
read -r -p "Library folder [Enter = $DEFAULT_LIB]: " LIBPATH || LIBPATH=""

DEFAULT_PORT="8077"
read -r -p "Port [Enter = $DEFAULT_PORT]: " PORT || PORT=""

.venv/bin/python init_config.py "$LIBPATH" "$PORT"

echo
echo "============================================================"
echo " Setup complete."
echo " Start genvault anytime with:"
echo "    ./genvault-tray.command   (double-click in Finder, or tray icon)"
echo " or directly in a terminal:"
echo "    .venv/bin/python serve.py"
echo "============================================================"
pause_if_gui
