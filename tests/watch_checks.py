"""Watch-folder checks (2.5.0): new renders are moved into the inbox, the
backlog stays until imported on request, Video Combine's companion PNG is
left in place, the folder structure is kept. run_tests.py configures one
watch folder (GV_TEST_WATCH) that already holds two "old" images."""
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core_checks import LIB, REGRESSION_FAILED, req  # noqa: E402  (runs the regression suite on import)

WATCH = Path(os.environ["GV_TEST_WATCH"])
MEDIA = Path(os.environ["GV_TEST_MEDIA"])
results = []


def check(name, cond, info=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info and not cond else ""))


def inbox_by_name():
    return {a["original_name"]: a for a in req("GET", "/api/assets?status=inbox")[1]["assets"]}


def watch_status():
    return req("GET", "/api/watch")[1]["folders"]


def wait_for(cond, timeout=45):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(1)
    return False


backlog = sorted((WATCH / "old").iterdir())
folders = watch_status()
check("one watch folder reported", len(folders) == 1 and folders[0]["ok"], folders)
w = folders[0]
check("existing files are counted as backlog", w["backlog_count"] == len(backlog) == 2 and w["backlog_bytes"] > 0, w)
check("backlog is NOT imported automatically", all(p.exists() for p in backlog)
      and not any(n.startswith("test image 1") and (a.get("source_hint") or "").startswith("watch:")
                  for n, a in inbox_by_name().items()))

# a new render: video + Video Combine's first-frame PNG, in a subfolder
sub = WATCH / "wan" / "day1"
sub.mkdir(parents=True)
shutil.copy(MEDIA / "test image 3.png", sub / "render_00001.png")     # copy(): fresh mtime, like a new render
shutil.copy(MEDIA / "test clip 3.mp4", sub / "render_00001.mp4")
shutil.copy(MEDIA / "test image 4.png", WATCH / "single_00001.png")    # an image without a video
shutil.copy(MEDIA / "test clip 4.mp4", sub / "late_00002.mp4")         # its PNG arrives only later
t_copy = time.time()

ok = wait_for(lambda: "render_00001.mp4" in inbox_by_name())
check("new render moved into the inbox", ok and not (sub / "render_00001.mp4").exists())
a = inbox_by_name().get("render_00001.mp4") or {}
check("source hint names the watch folder + subfolder", a.get("source_hint") == f"watch: {WATCH.name}/wan/day1", a.get("source_hint"))
check("file is in the inbox on disk", a and (LIB / a["rel_path"]).exists())
check("ComfyUI metadata parsed", (a.get("meta") or {}).get("positive_prompt", "").startswith("a test pattern"))
ok = wait_for(lambda: "late_00002.mp4" in inbox_by_name())
check("a file is only moved after it stayed unchanged for a few seconds", ok and time.time() - t_copy >= 3)
shutil.copy(MEDIA / "test image 1.png", sub / "late_00002.png")         # after its video is gone

ok = wait_for(lambda: "single_00001.png" in inbox_by_name())
check("a lone PNG is imported (after the companion grace period)", ok)
time.sleep(5)
check("the companion PNG stays in the watch folder", (sub / "render_00001.png").exists()
      and "render_00001.png" not in inbox_by_name())
check("a companion PNG that arrives after its video also stays", (sub / "late_00002.png").exists()
      and "late_00002.png" not in inbox_by_name())
check("watch folder structure is kept", sub.is_dir())
state = (LIB / ".config" / "watch-state.json").read_text(encoding="utf-8")
check("companion PNG is remembered across restarts", "render_00001.png" in state)
check("backlog still untouched", all(p.exists() for p in backlog) and watch_status()[0]["backlog_count"] == 2)

# validation
check("unknown watch folder -> 404", req("POST", "/api/watch/import", {"key": "C:/nope"})[0] == 404)
check("unknown watch action -> 404", req("POST", "/api/watch/explode", {"key": w["key"]})[0] == 404)

# dismiss + import the backlog on request
st, r, _ = req("POST", "/api/watch/dismiss", {"key": w["key"]})
check("dismiss the backlog banner", st == 200 and r["folders"][0]["dismissed"])
st, r, _ = req("POST", "/api/watch/import", {"key": w["key"]})
check("backlog import starts", st == 200)
ok = wait_for(lambda: not any(p.exists() for p in backlog) and not watch_status()[0]["importing"])
names = inbox_by_name()
check("backlog imported into the inbox", ok and all(p.name in names for p in backlog), [p.name for p in backlog])
fin = watch_status()[0]
check("backlog count is 0 afterwards", fin["backlog_count"] == 0 and (fin.get("job") or {}).get("done") == 2, fin)
inbox_all = req("GET", "/api/assets?status=inbox")[1]["assets"]
check("hint for backlog files", any(x["original_name"] == backlog[0].name and x.get("source_hint") == f"watch: {WATCH.name}/old"
                                    for x in inbox_all), [(x["original_name"], x.get("source_hint")) for x in inbox_all])

failed = [n for n, ok in results if not ok]
print(f"\nwatch folders: {len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed or REGRESSION_FAILED else 0)
