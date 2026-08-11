import os
from core.duplicate import SKIP_DIRS

def scan(target_path, min_size_mb=50, skip_system_dirs=True):
    """
    Scans target_path for files exceeding min_size_mb and returns a formatted report string.
    """
    min_bytes = min_size_mb * 1024 * 1024
    large_files = []

    for root, dirs, files in os.walk(target_path):
        if skip_system_dirs:
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for file in files:
            try:
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                if size >= min_bytes:
                    large_files.append((full_path, size))
            except (PermissionError, FileNotFoundError):
                continue

    if not large_files:
        return f"\nNo files larger than {min_size_mb} MB were found in:\n{target_path}"

    # Sort files by size (largest first)
    large_files.sort(key=lambda x: x[1], reverse=True)

    output = [f"\nFound {len(large_files)} file(s) larger than {min_size_mb} MB:\n"]
    output.append(f"{'Size (MB)':<12} | {'File Path'}")
    output.append("-" * 75)

    total_bytes = 0
    for path, size in large_files:
        size_mb = size / (1024 * 1024)
        total_bytes += size
        output.append(f"{size_mb:>10.2f} MB | {path}")

    output.append("-" * 75)
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_bytes / (1024 * 1024 * 1024)
    output.append(f"Total Large Files Storage: {total_mb:.2f} MB ({total_gb:.2f} GB)")

    return "\n".join(output)

if __name__ == "__main__":
    # Test runner for standalone terminal execution
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Hp\Downloads"
    print(scan(test_path))