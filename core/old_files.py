import os
import time
from datetime import datetime
from core.duplicate import SKIP_DIRS

def scan(target_path, days_old=180, skip_system_dirs=True):
    """
    Scans target_path for files that haven't been modified in 'days_old' (default 6 months / 180 days).
    Returns a formatted report string for gui.py.
    """
    cutoff_time = time.time() - (days_old * 86400)  # 86400 seconds = 1 day
    old_files = []

    for root, dirs, files in os.walk(target_path):
        if skip_system_dirs:
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for file in files:
            try:
                full_path = os.path.join(root, file)
                mtime = os.path.getmtime(full_path)
                
                if mtime < cutoff_time:
                    size = os.path.getsize(full_path)
                    old_files.append((full_path, size, mtime))
            except (PermissionError, FileNotFoundError):
                continue

    if not old_files:
        return f"\nNo stale files older than {days_old} days were found in:\n{target_path}"

    # Sort files by oldest modified time first
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