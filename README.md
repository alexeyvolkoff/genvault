# genvault

A local catalog for your AI-generated videos, images and sounds — built for
people who produce a lot of ComfyUI / A1111 / Suno output and want to keep it
organized without handing it to a cloud service.

genvault runs a small web app on your own PC (`127.0.0.1`). Your media files
stay on your disk and are never uploaded anywhere.

**Platform:** Windows 10/11.

---

## Features

- **Inbox workflow** — new files land in an Inbox and are filed into
  *Project / Sub-project / Kind* by you. Nothing is sorted automatically, so
  your structure stays exactly the way you want it.
- **Three ways to import** — drag & drop into the browser window, drop files
  (or whole folders) into the watched `drop\` folder, or let genvault watch
  your ComfyUI output folder and pick up every new render automatically.
- **Review mode** — go through the Inbox one file at a time with the keyboard:
  keep or trash, rate, favorite, undo.
- **Metadata reader** — prompt, negative prompt, model, seed, sampler,
  scheduler, steps, CFG, shift and LoRAs are read from:
  - ComfyUI videos (graph in the `comment` tag, incl. Kijai WanVideoWrapper nodes)
  - ComfyUI and A1111 PNGs (text chunks)

  Every field is editable, plus a free-text notes field (handy for Suno
  styles or anything without embedded data).
- **Search & filters** — full-text search over prompts, tags, projects, LoRAs
  and file names; a project tree (project → sub-project) and
  sidebar facets with counts for kind, media type, character, LoRA and upload
  status.
- **Gallery** — video hover previews, audio waveform thumbnails with play
  button, star rating (1–5), favorites tab, "Top rated" sort.
- **Full-screen player** — watch the current view (or a selection) full
  screen, one file after another, with loop, sound and rating on the keyboard.
- **Bulk actions** — multi-select (Shift+click for a range) to file many
  inbox files at once, move library files to another project / sub-project /
  kind — also by dragging them onto the project tree — or delete them.
- **Rename projects and sub-projects** — from the sidebar; the files are moved
  along. Renaming onto an existing name merges the two.
- **Copy helpers** — "Copy prompt", "Copy all parameters", "Copy workflow JSON".
- **Upload tracking** — per platform (default: X, Civitai, Reddit) with post
  URL and date, for assets of kind `release`.
- **Release module** — select clips, trim seconds off their start or end,
  add a PNG watermark (9 positions, size, opacity, margins, preview frame),
  join several clips into one video, optionally replace the audio with silence,
  and render in the background. GPU (NVENC) encoding with automatic CPU
  fallback. Embedded prompts/workflows are stripped from rendered files.
- **Privacy blur** — one click blurs every preview, e.g. while screen sharing.
- **Safe by design** — deleting moves files to a Trash you can restore from;
  the database can be rebuilt at any time from per-file JSON sidecars; one-click
  backup of all metadata.

---

## Requirements

1. **Python 3.10 or newer** — <https://www.python.org/downloads/>
   During installation, tick **"Add python.exe to PATH"**.
2. **ffmpeg** (for thumbnails, video metadata and the release module)
   - Download `ffmpeg-release-essentials.zip` from <https://www.gyan.dev/ffmpeg/builds/>
   - Unzip it and copy `ffmpeg.exe` and `ffprobe.exe` into `C:\ffmpeg\bin`
     (or put them anywhere on your `PATH`).
3. An internet connection when opening the app: the page styling (Tailwind
   CSS) is loaded from a CDN. Your media is never sent anywhere.

---

## Installation

1. Unzip the download and move the `genvault` folder to where it should live
   permanently (e.g. `D:\genvault`).
2. Double-click **`setup.bat`**. It will
   - create a private Python environment in `.venv` (takes 1–2 minutes),
   - ask **where your library should live** — all imported media goes there,
     so pick a drive with enough space (press Enter for `%USERPROFILE%\genvault`),
   - ask for the port (press Enter for `8077`).

## Starting and stopping

- Start: double-click **`genvault-tray.bat`**. A tray icon appears
  (gray = starting, green = running). Right-click it → **Open genvault**, or open
  <http://127.0.0.1:8077> in your browser.
- Stop: right-click the tray icon → **Quit**.

---

## Using genvault

1. **Import** — drag files into the browser window, or put them into
   `<library>\drop\`. Everything appears in the **Inbox**. To pick up your
   renders automatically, add your ComfyUI output folder as a *watch folder*
   (see [Watch folders](#watch-folders)).
   **Sort out the junk first:** click **▶ Review** in the Inbox and go through
   the files with the keyboard — **Enter** keep, **Del** trash,
   **← / →** back / next (no decision), **Z** undo, **F** favorite,
   **1–5** rating, **M** sound, **Esc** finish. At the end, **Enter** selects the files you kept, ready to be
   filed.
2. **File** — in the Inbox, enter a project and pick a kind for each file
   (sub-project, character and tags are optional), then click
   **Add to library**. For many files: tick their checkboxes and use the bar at
   the bottom.
3. **Browse** — the **Library** tab has search at the top and filters on the
   left. Click a card to open its details.
4. **Watch** — **▶ Play** (Library toolbar) plays the files you see, or only
   the selected ones, full screen: **← / →** previous / next, **Space** pause,
   **A** loop, **M** sound, **V** videos only, **I** info, **F** / **1–5**
   favorite and rating, **Esc** exit. Images stay 5 seconds; after the last
   file it starts over. The icons in the top right show loop / sound /
   videos-only.
5. **Details** — rate, favorite, edit metadata, copy the prompt, change the
   assignment (the file is moved on disk), track uploads. Click the file path
   to open it in Explorer.
6. **Move many files** — tick cards in the Library (Shift+click selects a
   range) and either **drag them onto a project or sub-project in the left
   sidebar**, or fill in only the fields you want to change in the bottom bar
   (empty fields keep their value; **none** moves them out of their
   sub-project) and click **Move**. The ▸ arrow next to a project shows its
   sub-projects.
7. **Release** — tick video cards → **Create release**. Per clip you can enter
   how many seconds to **cut** from its start and end (the remaining length is
   shown right away) — or click **✂ Preview** to play the clip, step frame by
   frame, and set the cuts with **Set start here** / **Set end here** (the frame
   you see is always kept); **Play trimmed** plays only the part that stays. Upload a watermark logo (PNG), set position/size/opacity,
   order the clips by drag & drop, pick **Audio: Keep original** or **Replace
   with silence**, choose the destination (a project or any folder) and click
   **Start render**. A single clip can also be exported with only a trim or
   only silent audio. Progress is shown in the render queue; genvault stays
   usable meanwhile.
8. **Rename a project or sub-project** — hover over it in the left sidebar
   and click the ✎ pencil. All its files (including ones in the Trash) follow
   the new name; if the new name already exists, both are merged.
9. **Delete** — via the details panel, or tick several cards and click
   **Delete (N)** in the bottom bar. Files go to the **Trash** tab, where you can
   select them again to **Restore** or **Delete forever** —
   one by one or many at once — or **Empty trash**. Deleting forever cannot be
   undone.

### Keyboard shortcuts

`1`–`5` rating · `F` favorite · `←` / `→` previous / next in the details panel ·
`Esc` close. Shortcuts are ignored while typing in a text field; without an
open details panel they apply to the card under the mouse. Review mode has its
own keys (see *Import* above; they are also shown at the bottom of the review
screen).

---

## Updating

1. Quit genvault (tray icon → Quit).
2. Drag the new genvault zip onto **`update.bat`** (or double-click it — it
   picks the newest `genvault*.zip` from your Downloads folder).
3. Start `genvault-tray.bat` again. The version is shown next to the logo.

Updates replace program files only. Your `config.json`, library and database
are never touched; database changes migrate automatically on start.

---

## Configuration

All settings are in the file **`config.json`** in the program folder (the
folder with `setup.bat`). To change them:

1. Right-click the genvault tray icon → **Edit config.json** (opens Notepad).
2. Change the value, save (Ctrl+S).
3. Tray icon → **Restart server**.

A complete `config.json` looks like this:

```
{
  "library_root": "D:\genvault-library",
  "port": 8077,
  "platforms": ["X", "Civitai", "Reddit"],
  "kinds": ["clip", "image", "sound", "release", "pre-release", "recipe"],
  "ffmpeg": "",
  "ffprobe": "",
  "watch_folders": []
}
```

| Setting | What it does |
|---|---|
| `library_root` | Folder that holds your media, database and thumbnails |
| `port` | Local web port (default `8077`) |
| `platforms` | Platforms shown in upload tracking |
| `kinds` | Kinds offered in the dropdowns (add your own here) |
| `ffmpeg`, `ffprobe` | Full paths to ffmpeg / ffprobe — only needed if they are not on `PATH` or in `C:\ffmpeg\bin` |
| `watch_folders` | Folders genvault imports new files from automatically, e.g. your ComfyUI output folder — see [Watch folders](#watch-folders) |

**Editing tips**

- Only change what is between the quotes `"…"` or the brackets `[…]`.
- Every line ends with a comma — except the last one before the closing `}`.
- Paths can be pasted straight from the Explorer address bar
  (`D:\ComfyUI\output`); forward slashes (`D:/ComfyUI/output`) work too.
- Made a mistake? genvault then **does not start** and the tray icon shows a
  message with the line number. Your library is not affected — fix the line
  and use **Restart server**.

You can run a second, separate instance (e.g. for testing) by copying the
program folder and giving it its own `library_root` and `port`.

### Watch folders

genvault can pick up your renders automatically: add the folder your
generator saves into (for ComfyUI: its `output` folder) as a *watch folder*.
Every new file there is then moved into the genvault Inbox.

**Set it up**

1. Open your ComfyUI `output` folder in Explorer, click into the address bar
   and copy the path (Ctrl+C), e.g. `D:\ComfyUI\output`.
   (Portable ComfyUI: `…\ComfyUI_windows_portable\ComfyUI\output`.)
2. Tray icon → **Edit config.json**. Near the end there is this line:

   ```
   "watch_folders": []
   ```

3. Put the path **in quotes** between the brackets:

   ```
   "watch_folders": ["D:\ComfyUI\output"]
   ```

   Several folders are separated by commas:
   `"watch_folders": ["D:\ComfyUI\output", "E:\renders"]`
4. Save, then tray icon → **Restart server**.
5. Open the **Inbox**. If the path is wrong, a yellow note says so. If the
   folder already contains files, a banner shows how many (see below).
   Render something — it appears in the Inbox a few seconds after ComfyUI has
   finished saving it.

(The `watch_folders` line is added to `config.json` automatically when
genvault 2.5.0 or newer starts for the first time.)

**What happens to the files**

- New files are **moved** into the Inbox as soon as they are completely
  written — no copies, so the folder empties itself and nothing exists twice.
  Subfolders are included; the folder structure itself is left alone.
- **Files that were already in the folder are not touched.** The Inbox shows
  how many there are, with **Import all** (moves them in the background, with
  progress and **Stop**) and **Ignore**.
- Video Combine saves a first-frame PNG next to every video. Such a PNG (same
  name as a video next to it) stays in the folder instead of being imported.
- ComfyUI's own history/queue previews can no longer show files after
  genvault has moved them.
- To stop watching a folder, remove it from the brackets and restart.
  Files that were already imported stay in genvault.

Advanced: to import those first-frame PNGs as well, write the folder as
`{ "path": "D:\ComfyUI\output", "skip_companion_png": false }` instead of just
the path. A watch folder must not be inside the genvault library (or contain it).

### Library layout

```
<library_root>\
├── drop\                       watched import folder (files are moved out)
├── _inbox\                     imported, not yet filed
├── library\<project>\<sub-project>\<kind>\   filed media
├── .trash\                     deleted files (restorable)
├── .derivatives\               thumbnails
├── .sidecars\                  one JSON per file — the database can be rebuilt from these
├── .config\                    release watermark, watch-folder state
├── backups\                    backup zips (Backup button)
└── genvault.db
```

Files are stored as `gv<id>_<original-name>.<ext>`; the original name is kept
and shown in the app.

---

## Troubleshooting

- **Page doesn't load** — is the tray icon green? Check `logs\server.log` in the
  program folder.
- **Tray says "config.json has an error"** — a typo in `config.json` (usually
  a missing or extra comma). The message names the line. Tray icon →
  **Edit config.json**, fix it, then **Restart server**. Your library is not
  affected.
- **No thumbnails / no video info** — ffmpeg isn't found (see Requirements).
- **"File is in use by another program"** — another app (player, editor) has
  the file open. Close it and try again.
- **Database looks wrong** — quit genvault, then run
  `.venv\Scripts\python.exe -m backend.db rebuild` in the program folder to
  rebuild it from the sidecars.
- **Prompt missing, or the negative prompt shows up as the positive one** —
  metadata reading is best effort. There is no standard for where ComfyUI
  workflows keep their prompts, so not every node setup can be read correctly.
  Fields stay empty when a file has no embedded workflow (saved without
  metadata, or re-encoded afterwards) or the prompt comes from an unknown node.
  Tip: give your text-encode nodes titles containing **"Positive"** and
  **"Negative"** — genvault checks these titles first. You can always correct
  the fields by hand in the details panel; "Copy workflow JSON" still returns
  the complete embedded workflow.

When reporting a problem, please include the version number shown next to the
logo and what you were doing.

---

## Technical notes

- Python backend (FastAPI + SQLite), plain JavaScript frontend with no build
  step. Server binds to `127.0.0.1` only.
- `backend\` — `config.py` (settings, version), `db.py` (SQLite, auto-migration,
  rebuild from sidecars), `parser.py` (metadata), `media.py` (thumbnails),
  `library.py` (import, filing, trash, backup), `fsutil.py` (Windows-safe file
  moves), `watcher.py` (drop + watch folders), `render.py` (release module), `main.py`
  (HTTP API). `web\` holds the frontend; `tray.py` is the tray launcher.
- Media is served with HTTP range support and share-delete file handles, so a
  file can be filed or deleted while it is playing in a preview.
- Release rendering: joining clips with identical codec/resolution/fps and no
  watermark or trim is a lossless stream copy; replacing the audio with silence
  keeps that video stream copy. Trimmed clips are always re-encoded so the cuts
  are frame-accurate. Everything else is re-encoded at the
  chosen quality — Standard (default; CRF 20 / NVENC CQ 21), High (17 / 17) or
  Near-lossless (5 / 10, very large files) — using the highest-resolution clip
  as target. Every output gets an AAC audio track (silence for silent clips)
  for web-player compatibility.
- There is no duplicate detection and no settings UI by design; see
  *Configuration*.

See `CHANGELOG.md` for the version history.

---

## Development

The repository contains the program plus two folders that are **not** part
of the release zip:

- `tests\` — integration checks. Run them with
  `.venv\Scripts\python.exe tests\run_tests.py`. The runner generates its own
  test media, starts a throwaway genvault server on port 8099 with a temporary
  library for every suite and removes everything afterwards; your
  `config.json` and your real library are never touched. Needs ffmpeg.
- `tools\` — `build_release.py` builds `genvault-<version>.zip` (program files
  only) from the current state; `demo\` generates a fictional sample library
  for screenshots.

Release checklist: bump `APP_VERSION` in `backend\config.py`, add a
`CHANGELOG.md` entry, run the tests, then build the zip.

---

## Contributing

genvault is a personal side project: a local media app for Windows, developed
at my own pace.

- **Bug reports and ideas are welcome** — open an issue on GitHub (please
  include the version number and what you were doing).
- **I don't accept pull requests for new features or other platforms**
  (macOS, Linux, integrations into other software). I can only maintain and
  test what I use myself.
- **Forks are welcome.** genvault is MIT-licensed — you may adapt it, port it
  or build it into your own project without asking. Please make clear that
  your version is a separate, independently maintained project.

---

## License

genvault is released under the [MIT License](LICENSE) — © 2026 fatberg_slim.

Python, ffmpeg and the libraries installed by `setup.bat` (FastAPI, Uvicorn,
watchdog, Pillow, pystray, python-multipart) are separate projects under their
own licenses; they are not bundled in this zip.
