import os
import hashlib
import time

# Reading in 1 MB chunks instead of 8 KB cuts down the number of Python-level
# loop iterations (and therefore CPU/GIL overhead) enormously on large files.
CHUNK_SIZE = 1024 * 1024

# Bytes sampled from the head/tail of a file for the cheap "pre-filter" hash.
PARTIAL_BYTES = 65536

# Folders that are (a) huge, (b) frequently permission-locked, and (c) almost
# never useful duplicate-scan targets. Skipping them keeps a scan of a broad
# path (e.g. a whole drive or user profile) fast and responsive instead of
# recursively hashing the entire OS/installed-software tree.
SKIP_DIRS = {
    "windows", "program files", "program files (x86)",
    "$recycle.bin", "system volume information", "programdata",
    "node_modules", ".git", "$windows.~bt", "$windows.~ws",
}


def _partial_hash(filepath, size):
    """Cheaply fingerprints a file using only its head + tail bytes.

    This lets us rule out the vast majority of same-size-but-different-content
    files without reading them in full, which is what previously caused a
    duplicate scan of a large/system path to read gigabytes of data off disk
    and stall the whole machine.
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            hasher.update(f.read(min(PARTIAL_BYTES, size)))
            if size > PARTIAL_BYTES * 2:
                f.seek(-PARTIAL_BYTES, os.SEEK_END)
                hasher.update(f.read(PARTIAL_BYTES))
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def get_file_hash(filepath, chunk_size=CHUNK_SIZE):
    """Calculates a full MD5 hash for a file in chunks to prevent high memory usage."""
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def duplicate_scan(file_records):
    """Return duplicate groups based on a file inventory from scanner.scan_files."""
    file_by_size = {}
    for item in file_records:
        try:
            file_by_size.setdefault(item.get('size', 0), []).append(item)
        except Exception:
            continue

    duplicates = []
    for size, group in file_by_size.items():
        if len(group) <= 1 or size <= 0:
            continue
        grouped_by_hash = {}
        for item in group:
            path = item.get('path')
            if not path or not os.path.exists(path):
                continue
            digest = get_file_hash(path)
            if digest:
                grouped_by_hash.setdefault(digest, []).append(item)
        for found_files in grouped_by_hash.values():
            if len(found_files) > 1:
                duplicates.append(found_files)
    return duplicates


def scan(target_path, stop_event=None, progress_cb=None, yield_every=25, skip_system_dirs=True):
    """
    Scans target_path for identical duplicate files and returns a detailed report.

    Uses a three-stage strategy so large/broad scan targets stay responsive:
      1) Group files by size (essentially free).
      2) Group same-size files by a cheap partial hash (head+tail, <=128 KB read).
      3) Only fully MD5-hash the files that already collided on BOTH size and
         partial hash -- i.e. only genuine duplicate candidates get read in full.

    ``progress_cb(stage, done, total)`` is called periodically (if provided) so
    a caller (e.g. the GUI) can show real progress instead of a fake animation.
    ``stop_event`` is checked frequently so a scan can be cancelled promptly.
    """
    size_map = {}
    scanned = 0

    for root, dirs, files in os.walk(target_path):
        if stop_event and stop_event.is_set():
            break

        if skip_system_dirs:
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]

        for file in files:
            if stop_event and stop_event.is_set():
                break
            full_path = os.path.join(root, file)
            try:
                size = os.path.getsize(full_path)
                size_map.setdefault(size, []).append(full_path)
            except (PermissionError, FileNotFoundError, OSError):
                continue

            scanned += 1
            if scanned % yield_every == 0:
                if progress_cb:
                    progress_cb("discover", scanned, None)
                time.sleep(0)  # yield the GIL/scheduler so the UI thread stays responsive

    # Stage 2: cheap partial-hash pre-filter, only on files that share a size.
    partial_map = {}
    candidates = [(size, group) for size, group in size_map.items() if len(group) > 1 and size > 0]
    total_candidates = sum(len(g) for _, g in candidates)
    processed = 0

    for size, file_list in candidates:
        if stop_event and stop_event.is_set():
            break
        for path in file_list:
            if stop_event and stop_event.is_set():
                break
            phash = _partial_hash(path, size)
            if phash:
                partial_map.setdefault((size, phash), []).append(path)

            processed += 1
            if processed % yield_every == 0:
                if progress_cb:
                    progress_cb("prefilter", processed, total_candidates)
                time.sleep(0)

    # Stage 3: full MD5 hash, only for real candidates (size AND partial hash match).
    hash_map = {}
    full_candidates = [(key, paths) for key, paths in partial_map.items() if len(paths) > 1]
    total_full = sum(len(paths) for _, paths in full_candidates)
    done_full = 0

    for (size, _phash), paths in full_candidates:
        if stop_event and stop_event.is_set():
            break
        for path in paths:
            if stop_event and stop_event.is_set():
                break
            file_hash = get_file_hash(path)
            if file_hash:
                hash_map.setdefault(file_hash, []).append((path, size))

            done_full += 1
            if done_full % yield_every == 0:
                if progress_cb:
                    progress_cb("hash", done_full, total_full)
                time.sleep(0)

    duplicate_groups = [group for group in hash_map.values() if len(group) > 1]

    if stop_event and stop_event.is_set():
        return f"\nDuplicate scan interrupted by user in:\n{target_path}"

    if not duplicate_groups:
        return f"\nNo duplicate files found in:\n{target_path}"

    total_removable_files = 0
    total_recoverable_bytes = 0
    output = [f"\nFound {len(duplicate_groups)} Duplicate Group(s):\n"]

    for idx, group in enumerate(duplicate_groups, start=1):
        original = group[0]
        duplicates = group[1:]
        size_kb = original[1] / 1024

        output.append(f"[Group {idx}] - File Size: {size_kb:.2f} KB")
        output.append(f"  └─ Original (KEPT)     : {original[0]}")

        for dup_path, dup_size in duplicates:
            total_removable_files += 1
            total_recoverable_bytes += dup_size
            output.append(f"  └─ Duplicate (REMOVABLE): {dup_path}")
        output.append("")

    output.append("-" * 75)
    rec_mb = total_recoverable_bytes / (1024 * 1024)
    rec_gb = total_recoverable_bytes / (1024 * 1024 * 1024)
    output.append(f"Total Removable Duplicates : {total_removable_files} files")
    output.append(f"Total Recoverable Space    : {rec_mb:.2f} MB ({rec_gb:.2f} GB)")

    return "\n".join(output)

if __name__ == "__main__":
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Hp\Downloads"
    print(scan(test_path))
