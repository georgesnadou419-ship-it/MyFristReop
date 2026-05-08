import os

import psutil


def collect_resource_info() -> dict:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    try:
        load_average = list(os.getloadavg())
    except (AttributeError, OSError):
        load_average = []

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "cpu_cores": psutil.cpu_count(logical=True) or 0,
        "load_average": load_average,
        "memory_total": int(memory.total / 1024 / 1024),
        "memory_used": int(memory.used / 1024 / 1024),
        "memory_available": int(memory.available / 1024 / 1024),
        "memory_percent": memory.percent,
        "disk_total": int(disk.total / 1024 / 1024),
        "disk_used": int(disk.used / 1024 / 1024),
        "disk_free": int(disk.free / 1024 / 1024),
        "disk_percent": disk.percent,
    }
