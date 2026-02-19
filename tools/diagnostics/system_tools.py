"""
System diagnostic tools – CPU, Memory, Disk.
All SAFE / read-only.
"""

from typing import Optional
import psutil

from tools.registry import registry


@registry.register(risk_level="SAFE", category="system")
def get_cpu_usage(process_name: Optional[str] = None) -> dict:
    """Get CPU usage percentage, optionally for a specific process."""
    try:
        if process_name:
            for proc in psutil.process_iter(["name", "cpu_percent"]):
                if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                    return {
                        "status": "success",
                        "data": {
                            "process": proc.info["name"],
                            "cpu_percent": proc.cpu_percent(interval=0.5),
                        },
                    }
            return {"status": "error", "message": f"Process '{process_name}' not found"}

        cpu = psutil.cpu_percent(interval=1)
        per_core = psutil.cpu_percent(interval=0, percpu=True)
        return {
            "status": "success",
            "data": {
                "cpu_percent": cpu,
                "per_core": per_core,
                "core_count": psutil.cpu_count(logical=True),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="system")
def get_memory_usage(process_name: Optional[str] = None) -> dict:
    """Get RAM usage, optionally for a specific process."""
    try:
        if process_name:
            for proc in psutil.process_iter(["name", "memory_info"]):
                if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                    mem = proc.info["memory_info"]
                    return {
                        "status": "success",
                        "data": {
                            "process": proc.info["name"],
                            "rss_mb": round(mem.rss / (1024 ** 2), 2),
                            "vms_mb": round(mem.vms / (1024 ** 2), 2),
                        },
                    }
            return {"status": "error", "message": f"Process '{process_name}' not found"}

        vm = psutil.virtual_memory()
        return {
            "status": "success",
            "data": {
                "total_gb": round(vm.total / (1024 ** 3), 2),
                "used_gb": round(vm.used / (1024 ** 3), 2),
                "available_gb": round(vm.available / (1024 ** 3), 2),
                "percent": vm.percent,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="system")
def get_disk_space(drive: str = "C:") -> dict:
    """Get disk space usage for a drive letter (default C:)."""
    try:
        path = f"{drive}\\" if not drive.endswith("\\") else drive
        usage = psutil.disk_usage(path)
        return {
            "status": "success",
            "data": {
                "drive": drive,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent": usage.percent,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
