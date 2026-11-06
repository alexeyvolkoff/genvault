"""System-tray launcher for genvault v2.

Runs the server as a child process (output -> logs/server.log, no console
window) and shows a tray icon that reflects real health: green when the
server answers, gray while it's down/starting. Launched without a console
via genvault-tray.bat (pythonw).
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
from backend.cfgfile import ConfigError, read as read_config_file  # noqa: E402  (no side effects)
PY = ROOT / ".venv" / "Scripts" / "python.exe"
SERVE = ROOT / "serve.py"
LOG_DIR = ROOT / "logs"
CREATE_NO_WINDOW = 0x08000000


CONFIG = ROOT / "config.json"
_config_error: str | None = None
PORT, URL, HEALTH = 8077, "", ""


def _read_config() -> dict:
    """Reads config.json and (re)sets PORT/URL; a broken file is remembered in
    _config_error so the server is not started with the default library."""
    global _config_error, PORT, URL, HEALTH
    try:
        cfg = read_config_file(CONFIG)
        _config_error = None
    except ConfigError as e:
        cfg, _config_error = {}, str(e)
    try:
        PORT = int(cfg.get("port", 8077))
    except (TypeError, ValueError):
        PORT = 8077
    URL = f"http://127.0.0.1:{PORT}"
    HEALTH = URL + "/api/health"
    return cfg


_read_config()

_proc: subprocess.Popen | None = None
_up = False


def _icon(up: bool) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, 58, 58), fill=(34, 197, 94, 255) if up else (120, 120, 130, 255))
    d.ellipse((24, 24, 40, 40), fill=(255, 255, 255, 235))
    return img


def _health() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _start_server():
    global _proc
    _read_config()
    if _config_error:
        return
    if _health():            # something already serving — don't double-start
        return
    if _proc and _proc.poll() is None:
        return
    LOG_DIR.mkdir(exist_ok=True)
    log = open(LOG_DIR / "server.log", "a", encoding="utf-8", buffering=1)
    _proc = subprocess.Popen(
        [str(PY), str(SERVE)],
        stdout=log, stderr=subprocess.STDOUT, cwd=str(ROOT),
        creationflags=CREATE_NO_WINDOW,
    )


def _stop_server():
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except Exception:
            _proc.kill()
    _proc = None


def _open(icon, item):
    webbrowser.open(URL)


def _open_library(icon, item):
    root = _read_config().get("library_root")
    if root and Path(os.path.expandvars(os.path.expanduser(root))).exists():
        os.startfile(os.path.expandvars(os.path.expanduser(root)))


def _restart(icon, item):
    _stop_server()
    _start_server()
    _report_config(icon)


def _edit_config(icon, item):
    subprocess.Popen(["notepad.exe", str(CONFIG)])


def _report_config(icon):
    if _config_error:
        icon.icon = _icon(False)
        icon.title = "genvault — not started: config.json has an error"
        try:
            icon.notify(_config_error.split("\n")[0] + "\nFix it via the tray menu → Edit config.json, then Restart server.",
                        "genvault did not start")
        except Exception:
            pass


def _quit(icon, item):
    _stop_server()
    icon.stop()


def _monitor(icon):
    global _up
    _report_config(icon)
    while True:
        if _config_error:
            time.sleep(2)
            continue
        up = _health()
        if up != _up:
            _up = up
            icon.icon = _icon(up)
            icon.title = f"genvault — running ({URL})" if up else "genvault — starting…"
        time.sleep(2)


def main():
    _start_server()
    icon = pystray.Icon(
        "genvault", _icon(False), "genvault — starting…",
        menu=pystray.Menu(
            pystray.MenuItem("Open genvault", _open, default=True),
            pystray.MenuItem("Restart server", _restart),
            pystray.MenuItem("Open library folder", _open_library),
            pystray.MenuItem("Edit config.json", _edit_config),
            pystray.MenuItem("Quit", _quit),
        ),
    )
    threading.Thread(target=_monitor, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()
