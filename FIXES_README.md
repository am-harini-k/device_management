# LapDoctor — Fixes Applied (Round 2)

## 1. Theme switching removed
It was breaking contrast/readability across the app (checkboxes disappearing,
low-contrast text, etc). The app now ships **Dark theme only** — the Settings
page no longer has a theme selector.

## 2. Settings page: About + Smart Cleaning added
- **About**: app version, license, a short description, and support
  contact/link.
- **Smart Cleaning**: a real toggle (not decorative). When on, a background
  thread checks your *actual* disk usage (via `psutil`) and does a cheap,
  extension-based scan of your Downloads folder for junk files
  (`.tmp/.log/.bak/.old/.dmp/.chk/...`) once a minute. If storage is ≥85% full
  or estimated junk exceeds ~200 MB, it raises a real pop-up alert (throttled
  to at most once every 15 minutes) telling you to run a cleanup scan. No
  files are ever touched automatically.

## 3. Scan Log Console fixed
Previously the console mixed everything together: file paths, "stop
requested" messages, start/complete banners, and cleanup results shared
across every scan mode. Now:
- The console only shows **scan results** (file paths / duplicate groups) —
  user-action and status chatter now lives only in the status line above the
  progress bar, not the console.
- **Each scan mode (Duplicates / Large Files / Old Files / App Caches) has
  its own separate console.** Switching the radio button switches which
  mode's last result you're viewing — a small "Showing results for: X" label
  confirms which one is displayed. Running a new scan for a mode replaces
  only that mode's console, leaving the others untouched.
- **Duplicates** console keeps the full grouped report — `[Group N] - File
  Size: ...`, `Original (KEPT)` / `Duplicate (REMOVABLE)` lines, and a totals
  footer — matching the format you asked for.
- **Large Files / Old Files / App Caches** consoles now show a plain list of
  file paths only, one per line.

## 4. UI misalignment / clipped text fixed
The clipped sidebar text, cut-off "START SCAN & ANALYZE" button, and the
garbled "Scan progress: 1009" you saw are classic symptoms of a Windows
high-DPI scaling mismatch in Tk apps. Fixed by:
- Declaring proper DPI awareness on Windows before any window is created
  (`SetProcessDpiAwareness`), so Tk measures text against the OS's real
  scaling factor instead of guessing.
- Widened the sidebar and locked its width (`grid_propagate(False)`) so its
  text can't get compressed.
- Gave the scan button a fixed minimum width and moved the mode radio
  buttons into their own sub-frame so they shrink instead of squeezing the
  button off-screen at narrower widths.
- Added `wraplength` to the analysis/status labels so long messages wrap
  instead of overflowing and overlapping neighboring widgets.

## 5. Responsiveness / lag fixed
Progress-callback UI updates are now **time-throttled** (max ~8 updates/sec)
instead of firing on every batch of files. On a fast scan over many small
files, the old code could queue hundreds of widget updates per second onto
the Tk event loop, which is what caused the stutter/lag during scanning.

## 6. Scan History page redesigned
Replaced the flat text-dump with a scrollable list of styled cards — one per
scan/cleanup event, each showing a type icon, a colored status badge
(Completed/In Progress/Stopped/Files Cleaned), the target path, timestamp,
and (for cleanups) files removed + space freed.

## Verified
All of the above was tested end-to-end in a headless X server (real
`mainloop()`, not simulated): scans run, per-mode consoles populate
correctly and independently, history cards render, Settings toggles work,
and no thread-safety errors occur. Screenshots were also captured to confirm
no clipped/overlapping text.
