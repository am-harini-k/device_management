import os
import time

from .duplicate import SKIP_DIRS

# Well-known cache/temp folder names we specifically call out when found
# inside the selected scan path, so results read like a real cache analysis
# instead of a single opaque folder-size total.
CACHE_HINTS = ("cache", "caches", "temp", "tmp", "logs", "crashdumps")


def scan(target_path=None, stop_event=None, progress_cb=None, yield_every=200, skip_system_dirs=True):
    """
    Scans a selected folder path (or default user folder) for cache / temp content.
    It should not auto-walk the whole system when the UI already points to a specific path.
    """
    selected_root = target_path or os.path.expanduser('~')

    if not os.path.exists(selected_root):
        return "\nSelected path does not exist."

    output = [f"\nAnalyzing Cache / Temporary Directories in: {selected_root}\n"]
    output.append(f"{'Cache / Category':<25} | {'Size (MB)':<10} | {'Path'}")
    output.append("-" * 85)

    total_system_cache = 0
    cache_hits = []
    other_bytes = 0
    scanned = 0

    try:
        for root, dirs, files in os.walk(selected_root):
            if stop_event and stop_event.is_set():
                break
            if skip_system_dirs:
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]

            folder_name = os.path.basename(root).lower()
            is_cache_dir = any(hint in folder_name for hint in CACHE_HINTS)

            for f in files:
                if stop_event and stop_event.is_set():
                    break
                try:
                    full_path = os.path.join(root, f)
                    size = os.path.getsize(full_path)
                except (PermissionError, FileNotFoundError, OSError):
                    continue

                total_system_cache += size
                if is_cache_dir:
                    cache_hits.append((root, size))
                else:
                    other_bytes += size

                scanned += 1
                if scanned % yield_every == 0:
                    if progress_cb:
                        progress_cb("discover", scanned, None)
                    time.sleep(0)
    except PermissionError:
        output.append(f"{'Selected Folder':<25} | {'Access Denied':<10} | {selected_root}")
        return "\n".join(output)

    if stop_event and stop_event.is_set():
        return f"\nCache scan interrupted by user in:\n{selected_root}"

    # Roll cache-hit files up by containing folder so the report reads as a
    # real per-cache-folder breakdown instead of one flat total.
    by_folder = {}
    for folder, size in cache_hits:
        by_folder[folder] = by_folder.get(folder, 0) + size

    if by_folder:
        for folder, size in sorted(by_folder.items(), key=lambda kv: kv[1], reverse=True):
            size_mb = size / (1024 * 1024)
            output.append(f"{'Cache/Temp Folder':<25} | {size_mb:>8.2f} MB | {folder}")
    else:
        size_mb = total_system_cache / (1024 * 1024)
        output.append(f"{'Selected Directory':<25} | {size_mb:>8.2f} MB | {selected_root}")

    output.append("-" * 85)
    total_mb = total_system_cache / (1024 * 1024)
    total_gb = total_system_cache / (1024 * 1024 * 1024)
    output.append(f"Total Cleanable App Caches: {total_mb:.2f} MB ({total_gb:.2f} GB)")

    return "\n".join(output)

if __name__ == "__main__":
    print(scan())
