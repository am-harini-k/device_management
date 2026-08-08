import os
from send2trash import send2trash


def execute(file_list=None):
    """Safely moves a list of files to the Windows Recycle Bin."""
    if not file_list:
        return "[Cleanup] No files provided for cleanup."

    recycled_count = 0
    freed_bytes = 0
    errors = []

    for file_path in file_list:
        # Standardize slashes: converts "D:/archive.zip" -> "D:\archive.zip"
        clean_path = os.path.abspath(os.path.normpath(file_path))

        if os.path.exists(clean_path):
            try:
                freed_bytes += os.path.getsize(clean_path)
                send2trash(clean_path)
                recycled_count += 1
            except Exception as e:
                errors.append(f"Failed to recycle {clean_path}: {str(e)}")
        else:
            errors.append(f"File does not exist: {clean_path}")

    freed_mb = round(freed_bytes / (1024**2), 2)
    summary = f"[Cleanup Success] Moved {recycled_count} file(s) to Recycle Bin. Freed ~{freed_mb} MB."

    if errors:
        summary += "\n\nErrors encountered:\n" + "\n".join(errors)

    return summary