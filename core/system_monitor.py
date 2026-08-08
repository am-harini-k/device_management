import psutil


def get_system_metrics():
    """Queries real-time hardware status using psutil."""
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    try:
        io = psutil.disk_io_counters()
        disk_activity = 0
        if io:
            disk_activity = min(100, max(0, round((io.read_bytes + io.write_bytes) / max(1, disk.total) * 100, 1)))
    except Exception:
        disk_activity = 0

    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.2),
            "cores": psutil.cpu_count(logical=True),
        },
        "ram": {
            "total_gb": round(vm.total / (1024**3), 2),
            "used_gb": round(vm.used / (1024**3), 2),
            "percent": vm.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
        },
        "storage": {
            "percent": disk.percent,
            "free_gb": round(disk.free / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2),
        },
        "disk_activity": {
            "percent": disk_activity,
        },
    }


def get_stats():
    """Compatibility wrapper used by the dashboard refresh loop."""
    metrics = get_system_metrics()
    return {
        "cpu": round(metrics.get("cpu", {}).get("percent", 0), 1),
        "ram_pct": round(metrics.get("ram", {}).get("percent", 0), 1),
        "disk_pct": round(metrics.get("disk_activity", {}).get("percent", 0), 1),
        "storage_pct": round(metrics.get("storage", {}).get("percent", 0), 1),
    }