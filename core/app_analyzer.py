import os

def scan():
    """
    Scans common Windows temp and app cache directories for bloated folders.
    """
    user_profile = os.environ.get("USERPROFILE", "")
    temp_dir = os.environ.get("TEMP", "")
    
    target_locations = {
        "User Temp Directory": temp_dir,
        "Windows Prefetch": r"C:\Windows\Prefetch",
        "VS Code Cache": os.path.join(user_profile, r"AppData\Roaming\Code\Cache"),
        "Google Chrome Cache": os.path.join(user_profile, r"AppData\Local\Google\Chrome\User Data\Default\Cache"),
        "Pip Package Cache": os.path.join(user_profile, r"AppData\Local\pip\cache")
    }

    output = ["\nAnalyzing System App Caches & Temporary Directories...\n"]
    output.append(f"{'Cache / Category':<25} | {'Size (MB)':<10} | {'Path'}")
    output.append("-" * 85)

    total_system_cache = 0

    for category, path in target_locations.items():
        if not path or not os.path.exists(path):
            output.append(f"{category:<25} | {'0.00 MB':<10} | [Directory Not Found]")
            continue

        folder_size = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        folder_size += os.path.getsize(os.path.join(root, f))
                    except (PermissionError, FileNotFoundError):
                        continue
        except PermissionError:
            output.append(f"{category:<25} | {'Access Denied':<10} | {path}")
            continue

        size_mb = folder_size / (1024 * 1024)
        total_system_cache += folder_size
        output.append(f"{category:<25} | {size_mb:>8.2f} MB | {path}")

    output.append("-" * 85)
    total_mb = total_system_cache / (1024 * 1024)
    total_gb = total_system_cache / (1024 * 1024 * 1024)
    output.append(f"Total Cleanable App Caches: {total_mb:.2f} MB ({total_gb:.2f} GB)")

    return "\n".join(output)

if __name__ == "__main__":
    print(scan())