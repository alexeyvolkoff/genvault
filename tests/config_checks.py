r"""config.json checks (2.5.0) — no server needed.

- Windows paths typed with single backslashes are accepted (also UNC paths
  and the "D:\new\folder" case that is valid JSON but means control chars)
- a broken file raises a clear ConfigError — it is never silently replaced by
  the defaults (that started genvault with an empty default library)
- serve.py refuses to start, init_config.py (setup) refuses to overwrite it
- add_missing() inserts new settings without touching the user's formatting
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.cfgfile import ConfigError, add_missing, read  # noqa: E402

BS = "\\"
results = []
tmp = Path(tempfile.mkdtemp(prefix="gv-config-"))


def check(name, cond, info=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info and not cond else ""))


def write(name, text):
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


def err(text):
    try:
        read(write("e.json", text))
    except ConfigError as e:
        return str(e)
    return None


check("normal file", read(write("a.json", '{"port": 8077, "watch_folders": ["D:/ComfyUI/output"]}'))
      == {"port": 8077, "watch_folders": ["D:/ComfyUI/output"]})
check("missing file -> {}", read(tmp / "nope.json") == {})
p = tmp / "bom.json"
p.write_bytes(b'\xef\xbb\xbf{"port": 1}')
check("UTF-8 BOM (Notepad) accepted", read(p) == {"port": 1})
single = '{"library_root": "D:' + BS + 'genvault", "watch_folders": ["D:' + BS + 'ComfyUI' + BS + 'output"]}'
check("single backslashes accepted", read(write("b.json", single))
      == {"library_root": "D:\\genvault", "watch_folders": ["D:\\ComfyUI\\output"]})
check(r'"D:\new\folder" is a path, not a newline',
      read(write("c.json", '{"x": ["D:' + BS + 'new' + BS + 'folder"]}')) == {"x": ["D:\\new\\folder"]})
check("UNC path typed as-is", read(write("d.json", '{"x": ["' + BS * 2 + 'nas' + BS + 'renders"]}'))
      == {"x": ["\\\\nas\\renders"]})
check("correct JSON escapes unchanged", read(write("f.json", '{"x": "D:' + BS * 2 + 'a' + BS * 2 + 'b"}')) == {"x": "D:\\a\\b"})

e = err('{\n  "port": 8077\n  "watch_folders": []\n}')
check("missing comma -> error with line number", e and "line 3" in e and "comma" in e, e)
e = err('{\n  "port": 8077,\n}')
check("trailing comma -> error", e and "line 3" in e, e)
check("not an object -> error", err('["D:/x"]'))

# serve.py must refuse a broken config instead of starting with the default library
broken = write("broken.json", '{\n  "library_root": "' + str(tmp / "lib").replace(BS, "/") + '",\n  "port": 8098\n  "x": 1\n}')
r = subprocess.run([sys.executable, "serve.py"], cwd=ROOT, capture_output=True, text=True, timeout=60,
                   env={**__import__("os").environ, "GENVAULT_CONFIG": str(broken)})
check("serve.py refuses a broken config.json", r.returncode == 2 and "NOT STARTED" in r.stdout, (r.returncode, r.stdout[-300:]))
check("...without creating the library", not (tmp / "lib").exists())

# setup (init_config.py) must not overwrite a config it cannot read
setup_dir = tmp / "setup"
(setup_dir / "backend").mkdir(parents=True)
shutil.copy2(ROOT / "init_config.py", setup_dir)
shutil.copy2(ROOT / "backend" / "cfgfile.py", setup_dir / "backend")
(setup_dir / "backend" / "__init__.py").write_text("", encoding="utf-8")
bad = '{\n  "library_root": "D:/mine"\n  "port": 8077\n}'
(setup_dir / "config.json").write_text(bad, encoding="utf-8")
r = subprocess.run([sys.executable, "init_config.py", "D:/other", "8077"], cwd=setup_dir, capture_output=True, text=True)
check("setup refuses to overwrite a broken config.json",
      r.returncode == 1 and (setup_dir / "config.json").read_text(encoding="utf-8") == bad, r.stdout)

# add_missing: old (pre-2.5) config gets "watch_folders": [] — nothing else changes
old = ('{\n  "library_root": "D:' + BS + 'genvault-library",\n  "port": 8077,\n'
       '  "platforms": ["X", "Civitai", "Reddit"],\n  "kinds": ["clip", "image"],\n  "ffmpeg": "",\n  "ffprobe": ""\n}\n')
p = write("old.json", old)
added = add_missing(p, {"watch_folders": []})
new = p.read_text(encoding="utf-8")
check("missing setting added", added == ["watch_folders"] and read(p)["watch_folders"] == [], new)
check("user's lines kept exactly", new.startswith(old.rstrip()[:-1].rstrip()) and new.rstrip().endswith("}"), new)
check("added line looks hand-written", '  "ffprobe": "",\n  "watch_folders": []\n}' in new, new)
check("second run changes nothing", add_missing(p, {"watch_folders": []}) == [] and p.read_text(encoding="utf-8") == new)
p = write("empty.json", "{}")
add_missing(p, {"watch_folders": []})
check("works on an empty {}", read(p) == {"watch_folders": []}, p.read_text(encoding="utf-8"))
p = write("broken2.json", '{"a": 1,}')
try:
    add_missing(p, {"watch_folders": []})
    check("broken file is not modified", False)
except ConfigError:
    check("broken file is not modified", p.read_text(encoding="utf-8") == '{"a": 1,}')

shutil.rmtree(tmp, ignore_errors=True)
failed = [n for n, ok in results if not ok]
print(f"\nconfig.json: {len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
