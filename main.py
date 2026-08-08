from quick_scan import quick_scan
from core.system_monitor import get_system_metrics
from core.cleanup import safe_delete_files

def fmt_size(size_bytes):
    if not size_bytes or size_bytes <= 0:
        return "0.00 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    s = float(size_bytes)
    while s >= 1024.0 and i < len(units) - 1:
        s /= 1024.0
        i += 1
    return f"{s:.2f} {units[i]}"

def display_duplicate_manifest(dupes):
    """
    Displays every duplicate group and candidate file for explicit user review.
    Returns a list of files that are safe and available for deletion.
    """
    print("\n" + "=" * 70)
    print("           DUPLICATE FILES REVIEW MANIFEST")
    print("=" * 70)
    
    candidates_for_deletion = []
    
    for group_idx, group in enumerate(dupes, start=1):
        print(f"\n[Group {group_idx}] - {len(group)} Identical Files (Size: {fmt_size(group[0]['size'])})")
        print(f"  └─ Original (KEPT) : {group[0]['path']}")
        
        # The remaining copies in the group are candidates for user cleanup
        for file_info in group[1:]:
            path = file_info["path"]
            is_protected = file_info.get("protected", False)
            
            if is_protected:
                reason = file_info.get("protection_reason", "Locked by process")
                print(f"  └─ Duplicate (PROTECTED - Cannot Delete): {path} [{reason}]")
            else:
                print(f"  └─ Duplicate (REMOVABLE)                : {path}")
                candidates_for_deletion.append(file_info)

    print("=" * 70)
    return candidates_for_deletion

def main():
    print("=" * 70)
    print("           LAPDOCTOR STORAGE MANAGEMENT SYSTEM")
    print("=" * 70)
    
    # 1. System Telemetry Check
    m = get_system_metrics()
    print(f"CPU: {m['cpu']['percent']}% | RAM: {m['ram']['percent']}% ({m['ram']['used_gb']}/{m['ram']['total_gb']} GB) | Disk: {m['disk']['percent']}%")
    print("-" * 70)

    # 2. Run Diagnostic Scan
    path = input("Enter path to scan (or press Enter for default folders): ").strip()
    results = quick_scan(path if path else None)

    dupes = results["duplicates"]
    rec_space = sum(g[0]["size"] * (len(g) - 1) for g in dupes)

    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print(f"Files Scanned      : {len(results['files']):,}")
    print(f"Duplicate Groups   : {len(dupes):,}")
    print(f"Large Files        : {len(results['large']):,}")
    print(f"Old Files          : {len(results['old']):,}")
    print(f"Installed Apps     : {len(results['apps']):,}")
    print(f"Potential Recovery : {fmt_size(rec_space)}")
    print(f"Scan Duration      : {results['duration']}s")
    print("=" * 70)

    # 3. User Review & Manual Action Safeguard
    if not dupes:
        print("\nNo duplicate files found. No cleanup action needed.")
        return

    # Present manifest for line-by-line inspection
    removable_files = display_duplicate_manifest(dupes)

    if not removable_files:
        print("\nAll detected duplicates are currently active or protected. No files eligible for deletion.")
        return

    # Explicit user prompt: Requires deliberate confirmation
    print(f"\nTotal Removable Duplicates : {len(removable_files)} files")
    print(f"Total Recoverable Space    : {fmt_size(sum(f['size'] for f in removable_files))}")
    
    confirm = input("\nTo move these files to the Recycle Bin, type 'YES': ").strip()
    
    if confirm == "YES":
        print("\nExecuting user-authorized cleanup...")
        summary = safe_delete_files(removable_files)
        print("-" * 70)
        print(f"Files Moved to Recycle Bin : {summary['success']}")
        print(f"Skipped (Active/Protected) : {summary['skipped']}")
        print(f"Failed                     : {summary['failed']}")
        print(f"Space Successfully Freed   : {fmt_size(summary['freed'])}")
        print("=" * 70)
    else:
        print("\nCleanup canceled. No files were modified or deleted.")

if __name__ == "__main__":
    main()