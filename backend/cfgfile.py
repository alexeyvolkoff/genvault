r"""Reading config.json — shared by the server, the tray launcher and setup.

Forgiving where it is safe, loud where it is not:
- Windows paths with single backslashes ("D:\ComfyUI\output") are not valid
  JSON. That is by far the most common editing mistake, so such a file is read
  again with every lone backslash treated as a path separator.
- Anything else that is not valid JSON raises ConfigError with the line and
  column. It is NEVER silently replaced by the defaults: that used to start
  genvault with an empty default library, which looks like all files are gone.
No side effects on import (the tray imports this before the server runs).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_PAIR_OR_LONE = re.compile(r"\\\\|\\")
_CONTROL = set("\b\f\n\r\t")


class ConfigError(Exception):
    """config.json exists but cannot be used."""


def _has_control_chars(obj) -> bool:
    if isinstance(obj, str):
        return any(c in _CONTROL for c in obj)
    if isinstance(obj, list):
        return any(_has_control_chars(x) for x in obj)
    if isinstance(obj, dict):
        return any(_has_control_chars(x) for x in obj.values())
    return False


_UNC_START = re.compile(r'"\\\\(?=[^\\"])')


def _paths_fixed(text: str) -> str:
    # a string starting with \\ is a network path (\\nas\share) typed as-is
    text = _UNC_START.sub(lambda m: '"' + "\\" * 4, text)
    # keep correct "\\" pairs, double every lone backslash
    return _PAIR_OR_LONE.sub(lambda m: m.group(0) if len(m.group(0)) == 2 else "\\\\", text)


def read(path: Path) -> dict:
    """Settings from config.json ({} if the file does not exist)."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8-sig")       # tolerate a BOM (Notepad)
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError(f"{path.name} cannot be read: {e}") from None
    return _parse(text, path.name)


def add_missing(path: Path, defaults: dict) -> list[str]:
    """Add settings a newer version introduced (e.g. "watch_folders": []) to an
    existing config.json, so users only have to fill them in. Only the new
    lines are inserted before the closing brace — the user's formatting and
    values stay as they are — and only if the result reads back correctly."""
    path = Path(path)
    if not path.exists():
        return []
    data = read(path)
    missing = [k for k in defaults if k not in data]
    if not missing:
        return []
    text = path.read_text(encoding="utf-8-sig")
    end = text.rfind("}")
    head = text[:end].rstrip()
    lines = "".join(f",\n  {json.dumps(k)}: {json.dumps(defaults[k])}" for k in missing)
    new = head + (lines[1:] if head.endswith("{") else lines) + "\n" + text[end:]
    try:
        if _parse(new, path.name) != {**data, **{k: defaults[k] for k in missing}}:
            return []
    except ConfigError:
        return []
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(new, encoding="utf-8")
    os.replace(tmp, path)
    return missing


def _parse(text: str, name: str) -> dict:
    try:
        data = json.loads(text)
        # "D:\new\folder" is valid JSON, but means a newline and a form feed
        if _has_control_chars(data):
            data = json.loads(_paths_fixed(text))
    except json.JSONDecodeError as e:
        try:
            data = json.loads(_paths_fixed(text))
        except json.JSONDecodeError:
            line = text.splitlines()[e.lineno - 1] if 0 < e.lineno <= len(text.splitlines()) else ""
            raise ConfigError(
                f"{name} has an error in line {e.lineno}, column {e.colno}: {e.msg}.\n"
                f"  {line.strip()}\n"
                "Common causes: a missing comma between two entries, a comma after the last "
                "entry, or a missing quote. genvault did not start, your library is untouched."
            ) from None
    if not isinstance(data, dict):
        raise ConfigError(f"{name} must contain {{ ... }} with the settings")
    return data
