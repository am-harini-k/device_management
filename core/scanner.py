import os
from pathlib import Path

DEFAULT_FOLDERS = [
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Pictures",
    Path.home() / "Videos"
]

SKIP_FILES = {"desktop.ini", ".ds_store", "thumbs.db"}

def scan_files(target_dir=None):
    """Fast directory file discovery."""
    if target_dir:
        folders = [Path(target_dir)]
    else:
        folders = DEFAULT_FOLDERS

    files = []

    for folder in folders:
        if not folder.exists():
            continue

        dirs_to_scan = [str(folder)]
        while dirs_to_scan:
            current_dir = dirs_to_scan.pop()
            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        try:
                            if entry.name.startswith(('.', '$')) or entry.name.lower() in SKIP_FILES:
                                continue

                            if entry.is_dir(follow_symlinks=False):
                                dirs_to_scan.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                files.append({
                                    "name": entry.name,
                                    "path": entry.path,
                                    "size": stat.st_size,
                                    "modified": stat.st_mtime
                                })
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

    return files