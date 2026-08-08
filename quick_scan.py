import time
from core.scanner import scan_files
from core.duplicate import duplicate_scan
from core.large_files import find_large_files
from core.old_files import find_old_files
from core.app_analyzer import installed_apps

def quick_scan(target_dir=None):
    """Runs complete storage diagnostic scan[cite: 1]."""
    start = time.time()
    
    files = scan_files(target_dir)
    duplicates = duplicate_scan(files)
    large = find_large_files(files)
    old = find_old_files(files)
    apps = installed_apps()

    return {
        "files": files,
        "duplicates": duplicates,
        "large": large,
        "old": old,
        "apps": apps,
        "duration": round(time.time() - start, 2)
    }