import psutil

def get_system_metrics():
    """Queries real-time hardware status using psutil[cite: 1]."""
    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.2),
            "cores": psutil.cpu_count(logical=True)
        },
        "ram": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
            "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
            "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
            "percent": psutil.disk_usage('/').percent
        }
    }