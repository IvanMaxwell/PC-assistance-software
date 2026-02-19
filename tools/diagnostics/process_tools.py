"""
Process diagnostic tools – list, search, and inspect running processes.
All SAFE / read-only.
"""

from typing import Optional
import psutil

from tools.registry import registry


@registry.register(risk_level="SAFE", category="process")
def get_running_processes(sort_by: str = "memory", limit: int = 10) -> dict:
    """List running processes sorted by memory or cpu usage."""
    try:
        if sort_by not in ("memory", "cpu"):
            return {"status": "error", "message": "sort_by must be 'memory' or 'cpu'"}

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / (1024 ** 2), 2),
                    "status": info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key = "memory_mb" if sort_by == "memory" else "cpu_percent"
        procs.sort(key=lambda p: p[key], reverse=True)

        return {
            "status": "success",
            "data": {
                "total_processes": len(procs),
                "showing": min(limit, len(procs)),
                "sort_by": sort_by,
                "processes": procs[:limit],
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="process")
def get_process_details(process_name: Optional[str] = None, pid: Optional[int] = None) -> dict:
    """Get detailed info for a process by name or PID."""
    try:
        if pid:
            proc = psutil.Process(pid)
        elif process_name:
            matches = [p for p in psutil.process_iter(["name"])
                       if p.info["name"] and process_name.lower() in p.info["name"].lower()]
            if not matches:
                return {"status": "error", "message": f"Process '{process_name}' not found"}
            proc = matches[0]
        else:
            return {"status": "error", "message": "Provide process_name or pid"}

        with proc.oneshot():
            return {
                "status": "success",
                "data": {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "status": proc.status(),
                    "cpu_percent": proc.cpu_percent(interval=0.5),
                    "memory_mb": round(proc.memory_info().rss / (1024 ** 2), 2),
                    "create_time": proc.create_time(),
                    "num_threads": proc.num_threads(),
                    "exe": proc.exe() if proc.exe() else "N/A",
                },
            }
    except psutil.NoSuchProcess:
        return {"status": "error", "message": f"Process PID {pid} not found"}
    except psutil.AccessDenied:
        return {"status": "error", "message": "Access denied – run as administrator"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
