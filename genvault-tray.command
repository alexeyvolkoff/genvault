#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/local/bin:$PATH"

if [ ! -x ".venv/bin/python" ]; then
  echo "Please run ./setup.command first."
  if [ -t 0 ]; then
    read -r -p "Press Enter to close..." _ || true
  fi
  exit 1
fi

mkdir -p logs
if [ "$(uname -s)" = "Linux" ] && [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  exec .venv/bin/python serve.py
fi

nohup .venv/bin/python tray.py >> logs/tray.log 2>&1 </dev/null &
disown || true
echo "genvault launched in the background (check your menu bar / system tray)."
