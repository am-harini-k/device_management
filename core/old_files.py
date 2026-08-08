import os
import time
from datetime import datetime

from .duplicate import SKIP_DIRS


def find_old_files(file_records, days_old=180):
    """Return a list of records older than a cutoff based on mtime."""
    cutoff_time = time.time() - (days_old * 86400)
    return [item for item in file_records if item.get('modified', 0) < cutoff_time]


def scan(target_path, days_old=180, stop_event=None, progress_cb=None, yield_every=200, skip_system_dirs=True):
    """
    Scans target_path for files that haven't been modified in 'days_old' (default 6 months / 180 days).
    Returns a formatted report string for gui.py.
    """
    cutoff_time = time.time() - (days_old * 86400)
    old_files = []
    scanned = 0

    for root, dirs, files in os.walk(target_path):
        if stop_event and stop_event.is_set():
            break
        if skip_system_dirs:
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]

        for file in files:
            if stop_event and stop_event.is_set():
                break
            try:
                full_path = os.path.join(root, file)
                mtime = os.path.getmtime(full_path)

                if mtime < cutoff_time:
                    size = os.path.getsize(full_path)
                    old_files.append((full_path, size, mtime))
            except (PermissionError, FileNotFoundError, OSError):
                continue

            scanned += 1
            if scanned % yield_every == 0:
                if progress_cb:
                    progress_cb("discover", scanned, None)
                time.sleep(0)

    if stop_event and stop_event.is_set():
        return f"\nOld-file scan interrupted by user in:\n{target_path}"

    if not old_files:
        return f"\nNo stale files older than {days_old} days were found in:\n{target_path}"

    old_files.sort(key=lambda x: x[2])

    output = [f"\nFound {len(old_files)} stale file(s) older than {days_old} days:\n"]
    output.append(f"{'Last Modified':<12} | {'Size (MB)':<10} | {'File Path'}")
    output.append("-" * 80)

    total_bytes = 0
    for path, size, mtime in old_files:
        date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        size_mb = size / (1024 * 1024)
        total_bytes += size
        output.append(f"{date_str:<12} | {size_mb:>8.2f} MB | {path}")

    output.append("-" * 80)
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_bytes / (1024 * 1024 * 1024)
    output.append(f"Total Stale Files Storage: {total_mb:.2f} MB ({total_gb:.2f} GB)")

    return "\n".join(output)

if __name__ == "__main__":
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Hp\Downloads"
    print(scan(test_path))
