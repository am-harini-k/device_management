import os
import hashlib

# Folders that are (a) huge, (b) frequently permission-locked, and (c) almost
# never useful duplicate-scan targets. Skipping them keeps a scan of a broad
# path (e.g. a whole drive) fast and responsive instead of recursively
# hashing the entire OS/installed-software tree. Controlled by the
# "Exclude Windows / Program Files / recycle bin" checkbox in Settings.
SKIP_DIRS = {
    "windows", "program files", "program files (x86)",
    "$recycle.bin", "system volume information", "programdata",
    "node_modules", ".git",
}

def get_file_hash(filepath, chunk_size=8192):
    """Calculates MD5 hash for a file in chunks to prevent high memory usage."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError):
        return None

def scan(target_path, skip_system_dirs=True):
    """
    Scans target_path for identical duplicate files and returns a detailed report.
    """
    size_map = {}
    
    # Step 1: Quick filter - group files by exact size
    for root, dirs, files in os.walk(target_path):
        if skip_system_dirs:
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for file in files:
            full_path = os.path.join(root, file)
            try:
                size = os.path.getsize(full_path)
                size_map.setdefault(size, []).append(full_path)
            except (PermissionError, FileNotFoundError):
                continue

    # Step 2: Scientific filter - calculate hash for files sharing the same size
    hash_map = {}
    for size, file_list in size_map.items():
        if len(file_list) > 1 and size > 0:  # Only hash if multiple files have the same size
            for path in file_list:
                file_hash = get_file_hash(path)
                if file_hash:
                    hash_map.setdefault(file_hash, []).append((path, size))

    # Step 3: Extract duplicate groups
    duplicate_groups = [group for group in hash_map.values() if len(group) > 1]
    
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