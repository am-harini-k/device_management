# LapDoctor — Fixes Applied

## 1. Duplicate scan freezing the GUI / whole laptop
**Cause:** `core/duplicate.py` computed a full MD5 hash (reading the *entire*
file) for every file that merely shared a size with another file. On a large
or system-wide path this means reading huge amounts of data off disk, which
saturates I/O and stalls the whole machine, not just the app.

**Fix:** `core/duplicate.py` now uses a 3-stage pipeline:
1. Group by file size (free).
2. Cheap **partial hash** — only reads the first + last 64 KB of each
   same-size file — to rule out non-duplicates without full reads.
3. Only files that collide on *both* size and partial hash get a full
   MD5 hash.

It also now skips known noisy/protected folders (`Windows`,
`Program Files`, `$Recycle.Bin`, `System Volume Information`,
`node_modules`, `.git`, ...) by default, yields control periodically so the
OS/UI stay responsive, and reports real progress via a `progress_cb`
callback instead of blocking silently. The same skip-list + progress
pattern was applied to `large_files.py`, `old_files.py`, and
`app_analyzer.py` for consistency.

A new checkbox in **Settings** lets you turn the system-folder skip off if
you deliberately want to scan those locations.

## 2. Theme switching not applying
**Cause:** every color in `gui.py` was a hardcoded hex string, so
`ctk.set_appearance_mode()` had no visible effect on the UI.

**Fix:** added a real `apply_theme()` in `gui.py` that walks the live widget
tree and swaps each *matching* palette color for its Dark/Light equivalent.
Layout, structure, and every widget stay exactly where they were — only the
surface/text tones change. Status colors (red/green/amber badges) and the
brand accent are intentionally kept constant across both themes.

## 3. Static / placeholder UI elements made real
- Dashboard **Health Score** was a fixed `82 / 100` — now computed live from
  real CPU/RAM/storage usage (`psutil`, via `core/system_monitor.py`, which
  was already real).
- Dashboard **Storage Analysis Summary** never updated after a scan — it now
  reflects the actual last scan's results.
- The scan progress bar was a fake time-based animation — it's now driven by
  the scanner's real discover/pre-filter/hash stage progress.
- Removed a dead, unused code path (`run_duplicate_scanner`).

## Not changed
- Overall layout, page structure, navigation, and visual design are
  untouched, as requested — only the bugs above were fixed and the theme
  colors now actually apply.
- `lapdoctor_cache.db` was removed from this package because it contained an
  orphaned, unused table left over from earlier testing; the app recreates a
  fresh one automatically on first run.
