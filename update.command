#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/local/bin:$PATH"

echo "=== genvault updater (macOS / Linux) ==="
echo

pause_if_gui() {
  if [ -t 0 ]; then
    echo
    read -r -p "Press Enter to close..." _ || true
  fi
}

if [ ! -f "serve.py" ]; then
  echo "ERROR: this does not look like a genvault folder."
  echo "Put update.command inside your genvault folder and run it from there."
  pause_if_gui
  exit 1
fi

ZIP="${1:-}"
if [ -z "$ZIP" ]; then
  echo "Looking for the newest genvault*.zip in ~/Downloads..."
  ZIP="$(ls -t "$HOME"/Downloads/genvault*.zip 2>/dev/null | head -n 1 || true)"
fi

if [ -z "$ZIP" ] || [ ! -f "$ZIP" ]; then
  echo "Could not find an update zip."
  echo "Pass the zip path to ./update.command <file.zip>, or put genvault*.zip in ~/Downloads."
  pause_if_gui
  exit 1
fi

echo "Using update: $ZIP"
echo
echo "IMPORTANT: quit genvault first (menu bar / tray icon -> Quit)."
if [ -t 0 ]; then
  read -r -p "Press Enter once genvault is closed (or Ctrl+C to cancel)..." _
fi

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/genvault-update.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

echo "Extracting..."
unzip -q "$ZIP" -d "$STAGE"

SRC="$STAGE/genvault"
if [ ! -f "$SRC/serve.py" ]; then
  for d in "$STAGE"/*; do
    if [ -d "$d" ] && [ -f "$d/serve.py" ]; then
      SRC="$d"
      break
    fi
  done
fi
if [ ! -f "$SRC/serve.py" ] && [ -f "$STAGE/serve.py" ]; then
  SRC="$STAGE"
fi
if [ ! -f "$SRC/serve.py" ]; then
  echo "ERROR: that zip does not contain a genvault install."
  pause_if_gui
  exit 1
fi

echo "Updating files (preserving config.json, .venv, logs, library)..."
rsync -a \
  --exclude 'config.json' \
  --exclude 'update.command' \
  --exclude '.venv' \
  --exclude 'logs' \
  --exclude '__pycache__' \
  --exclude '.git' \
  "$SRC"/ ./

chmod +x setup.command genvault-tray.command update.command 2>/dev/null || true

echo "Refreshing dependencies..."
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m pip install -r requirements.txt --quiet --disable-pip-version-check
else
  echo "No .venv yet — running first-time setup instead."
  ./setup.command
  exit 0
fi

echo
echo "============================================================"
echo " Update complete. Start genvault as usual:"
echo "    ./genvault-tray.command"
echo "============================================================"
pause_if_gui
