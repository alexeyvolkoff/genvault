r"""Folder watcher: drop\ plus the optional watch folders from config.json.

drop\:  every file (also whole folders, recursively) is moved into the inbox
        once its size is stable; emptied subfolders are removed.
watch folders (2.5.0, e.g. the ComfyUI output folder): new files are moved
        into the inbox the same way, the folder structure is left alone.
        Files that were already there when the folder was first watched are
        the *backlog*: they are only counted, and imported on request
        (status/import/stop/dismiss below, shown as a banner in the Inbox).
        With skip_companion_png, the first-frame PNG that Video Combine saves
        next to every video is left in place instead of being imported.

The subfolder path is recorded as a non-binding display hint only — it is
NEVER used to derive project/kind.

watchdog events just wake the worker; the actual intake decision is a
size-stability check across two scans, so half-written videos are left alone.
State that must survive restarts (when a folder was first watched, skipped
companion PNGs, dismissed backlog banners) lives in .config\watch-state.json.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import config, library

SCAN_INTERVAL = 4.0          # fallback scan cadence in seconds
IGNORE_SUFFIXES = (".part", ".crdownload", ".tmp", ".partial")
COMPANION_GRACE = 15.0       # a PNG waits this long for its video to appear
BACKLOG_SLICE = 3.0          # seconds of backlog import per loop (new renders keep flowing)

_wake = threading.Event()
_started = False
_observer: Observer | None = None
_scheduled: set[str] = set()
_last_seen: dict[str, tuple[int, int]] = {}      # path -> (size, mtime_ns) of the previous scan
_state_lock = threading.Lock()
_state: dict = {"folders": {}, "skip": []}
_skip: set[str] = set()
_dirty = False                                    # state changed, write it after the scan
_status: dict[str, dict] = {}                     # per watch folder, filled by the worker
_backlog_jobs: dict[str, dict] = {}               # key -> {"done", "failed", "failed_paths"}


class _Handler(FileSystemEventHandler):
    def on_any_event(self, event):
        _wake.set()


def _key(p: Path) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


# ---- persistent state ------------------------------------------------------------


def _state_file() -> Path:
    return config.LIBRARY_ROOT / ".config" / "watch-state.json"


def _load_state() -> None:
    global _state, _skip
    try:
        _state = json.loads(_state_file().read_text(encoding="utf-8"))
    except Exception:
        _state = {}
    _state.setdefault("folders", {})
    _state.setdefault("skip", [])
    # forget skipped companions that no longer exist
    _skip = {s for s in _state["skip"] if os.path.exists(s)}


def _save_state() -> None:
    global _dirty
    _dirty = False
    with _state_lock:
        _state["skip"] = sorted(_skip)
        f = _state_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(_state, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, f)


# ---- sources ---------------------------------------------------------------------


def _problem(path: Path) -> str | None:
    """Why a watch folder can't be used (None = fine)."""
    try:
        p = Path(os.path.abspath(str(path)))
        root = Path(os.path.abspath(str(config.LIBRARY_ROOT)))
    except Exception as e:
        return f"invalid path: {e}"
    kp, kr = _key(p), _key(root)
    inside = lambda a, b: a == b or a.startswith(b.rstrip(os.sep) + os.sep)   # (b may be "d:\")
    if inside(kp, kr):
        return "is inside the genvault library — files would be imported in a loop"
    if inside(kr, kp):
        return "contains the genvault library — files would be imported in a loop"
    return None


def _sources() -> list[dict]:
    src = [{"path": config.DROP_DIR, "drop": True, "skip_companion_png": False}]
    for w in config.WATCH_FOLDERS:
        src.append({"path": w["path"], "drop": False, "skip_companion_png": w["skip_companion_png"]})
    return src


def _walk(root: Path):
    """(path, size, mtime_ns) of all candidate files below root. scandir keeps
    this cheap on big output folders (no extra stat call per file on Windows)."""
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            continue
        with it:
            for e in it:
                name = e.name.lower()
                if name.startswith((".", "~")):
                    continue
                try:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(Path(e.path))
                        continue
                    if not e.is_file(follow_symlinks=False) or name.endswith(IGNORE_SUFFIXES):
                        continue
                    st = e.stat()
                except OSError:
                    continue
                yield Path(e.path), st.st_size, st.st_mtime_ns


def _hint_for(p: Path, src: dict) -> str | None:
    root = src["path"]
    rel = str(p.parent.relative_to(root)).replace("\\", "/")
    if src["drop"]:
        return rel if rel != "." else None
    return f"watch: {root.name}" + (f"/{rel}" if rel != "." else "")


def _video_stems(files) -> set[tuple[str, str]]:
    """(folder, stem) of every video — a PNG with the same stem (or the stem of
    Video Combine's "-audio" variant) is that video's first-frame companion."""
    out = set()
    for p, _, _ in files:
        if config.media_type_for(p) == "video":
            stem = p.stem.lower()
            out.add((_key(p.parent), stem))
            if stem.endswith("-audio"):
                out.add((_key(p.parent), stem[: -len("-audio")]))
    return out


def _is_companion(p: Path, stems: set) -> bool:
    return p.suffix.lower() == ".png" and (_key(p.parent), p.stem.lower()) in stems


def _mark_skip(p: Path) -> None:
    global _dirty
    _skip.add(_key(p))
    _dirty = True


def _import(p: Path, src: dict, stems: set) -> bool:
    if src["skip_companion_png"] and config.media_type_for(p) == "video":
        # remember the companion PNG before the video leaves the folder —
        # afterwards nothing would tell it apart from a normal image
        stem = p.stem[: -len("-audio")] if p.stem.lower().endswith("-audio") else p.stem
        png = p.with_name(stem + ".png")
        if png.exists():
            _mark_skip(png)
    asset = library.intake(p, hint=_hint_for(p, src), move=True)
    if not asset:
        print(f"[watcher] unsupported file type, leaving it: {p.name}")
    return bool(asset)


# ---- scanning ----------------------------------------------------------------------


def _cleanup_empty_dirs() -> None:
    for d in sorted(config.DROP_DIR.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()  # only succeeds when empty
            except OSError:
                pass


def _ensure_scheduled(path: Path) -> None:
    k = _key(path)
    if _observer is None or k in _scheduled or not path.is_dir():
        return
    try:
        _observer.schedule(_Handler(), str(path), recursive=True)
        _scheduled.add(k)
    except Exception as e:
        print(f"[watcher] cannot watch {path}: {e} (falling back to periodic scans)")
        _scheduled.add(k)


def _scan_source(src: dict, seen: dict) -> int:
    root: Path = src["path"]
    k = _key(root)
    st = None
    if not src["drop"]:
        st = _status.setdefault(k, {})
        st.update({"path": str(root), "skip_companion_png": src["skip_companion_png"]})
        problem = _problem(root)
        if problem or not root.is_dir():
            st.update({"ok": False, "error": problem or "folder not found",
                       "backlog_count": 0, "backlog_bytes": 0})
            return 0
        st.update({"ok": True, "error": None})
        with _state_lock:
            info = _state["folders"].get(k)
        if info is None:
            # first time this folder is watched: everything already in it is backlog
            info = {"since": time.time_ns(), "dismissed": False}
            with _state_lock:
                _state["folders"][k] = info
            _save_state()
            print(f"[watcher] now watching {root} — existing files are left alone (backlog)")
        since = int(info["since"])
    _ensure_scheduled(root)

    files = [f for f in _walk(root) if config.media_type_for(f[0])]
    stems = _video_stems(files) if src["skip_companion_png"] else set()
    now_ns = time.time_ns()
    imported = 0
    backlog = []
    for p, size, mtime in files:
        pk = _key(p)
        if pk in _skip:
            continue
        if src["skip_companion_png"] and _is_companion(p, stems):
            _mark_skip(p)
            continue
        if not src["drop"] and mtime < since:
            backlog.append((p, size))
            continue
        seen[str(p)] = (size, mtime)
        if _last_seen.get(str(p)) != (size, mtime):
            continue                                  # new or still growing
        if (src["skip_companion_png"] and p.suffix.lower() == ".png"
                and now_ns - mtime < COMPANION_GRACE * 1e9):
            continue                                  # its video may not exist yet
        try:
            if _import(p, src, stems):
                imported += 1
            else:
                seen.pop(str(p), None)
        except Exception as e:
            print(f"[watcher] intake failed for {p.name}: {e}")

    if st is not None:
        st["backlog_count"] = len(backlog)
        st["backlog_bytes"] = sum(s for _, s in backlog)
        st["dismissed"] = bool(info.get("dismissed"))
        job = _backlog_jobs.get(k)
        if job is not None:
            imported += _import_backlog_slice(backlog, src, stems, job)
            st["backlog_count"] = sum(1 for p, _ in backlog if p.exists())
            st["backlog_bytes"] = sum(s for p, s in backlog if p.exists())
            if not any(p.exists() and _key(p) not in job["failed_paths"] for p, _ in backlog):
                job["finished"] = True
            if job.get("finished"):
                _backlog_jobs.pop(k, None)
                print(f"[watcher] backlog import {'stopped' if job.get('stop') else 'finished'} "
                      f"for {root}: {job['done']} imported, {job['failed']} failed")
        st["importing"] = k in _backlog_jobs
        # the last job stays visible (progress / result line in the Inbox banner)
        if job is not None:
            st["job"] = {x: v for x, v in job.items() if x != "failed_paths"}
    return imported


def _import_backlog_slice(backlog, src, stems, job) -> int:
    t0 = time.monotonic()
    n = 0
    for p, _ in backlog:
        if time.monotonic() - t0 > BACKLOG_SLICE or job.get("stop"):
            break
        pk = _key(p)
        if pk in job["failed_paths"] or not p.exists():
            continue
        try:
            if _import(p, src, stems):
                n += 1
                job["done"] += 1
            else:
                job["failed_paths"].add(pk)
        except Exception as e:
            job["failed"] += 1
            job["failed_paths"].add(pk)
            print(f"[watcher] backlog intake failed for {p.name}: {e}")
    if job.get("stop"):
        job["finished"] = True
    return n


def _scan_once() -> None:
    global _last_seen
    seen: dict = {}
    imported = 0
    for src in _sources():
        try:
            n = _scan_source(src, seen)
        except Exception as e:
            print(f"[watcher] scan error in {src['path']}: {e}")
            continue
        imported += n
        if src["drop"] and n:
            _cleanup_empty_dirs()
    _last_seen = seen
    if _dirty:
        _save_state()
    if imported:
        print(f"[watcher] imported {imported} file(s) into the inbox")


def _worker() -> None:
    while True:
        # keep going without pause while a backlog import is running
        if not _backlog_jobs:
            _wake.wait(timeout=SCAN_INTERVAL)
        _wake.clear()
        try:
            _scan_once()
        except Exception as e:
            print(f"[watcher] scan error: {e}")


def start() -> None:
    global _started, _observer
    if _started:
        return
    _started = True
    config.ensure_dirs()
    _load_state()
    _observer = Observer(timeout=2)
    _observer.daemon = True
    _observer.start()
    for src in _sources():
        _ensure_scheduled(src["path"])
    threading.Thread(target=_worker, daemon=True, name="gv-drop-worker").start()
    print(f"[watcher] watching {config.DROP_DIR}"
          + "".join(f", {w['path']}" for w in config.WATCH_FOLDERS))


# ---- API helpers (used by main.py) ----------------------------------------------------


def status() -> list[dict]:
    out = []
    for w in config.WATCH_FOLDERS:
        k = _key(w["path"])
        st = dict(_status.get(k) or {"path": str(w["path"]), "ok": None, "error": None,
                                     "backlog_count": 0, "backlog_bytes": 0})
        st["key"] = k
        st.setdefault("importing", k in _backlog_jobs)
        out.append(st)
    return out


def _known(key: str) -> str:
    for w in config.WATCH_FOLDERS:
        if _key(w["path"]) == key or str(w["path"]) == key:
            return _key(w["path"])
    raise LookupError("not a configured watch folder")


def import_backlog(key: str) -> None:
    k = _known(key)
    if k not in _backlog_jobs:
        _backlog_jobs[k] = {"done": 0, "failed": 0, "failed_paths": set(), "started": time.time()}
    _wake.set()


def stop_backlog(key: str) -> None:
    job = _backlog_jobs.get(_known(key))
    if job:
        job["stop"] = True
    _wake.set()


def dismiss_backlog(key: str, dismissed: bool = True) -> None:
    k = _known(key)
    with _state_lock:
        info = _state["folders"].setdefault(k, {"since": time.time_ns()})
        info["dismissed"] = bool(dismissed)
    _save_state()
    if k in _status:
        _status[k]["dismissed"] = bool(dismissed)
