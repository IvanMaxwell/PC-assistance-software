"""
Process action tools – kill and restart processes.
Risk: HIGH (can crash applications).
"""

import psutil

from tools.registry import registry


@registry.register(risk_level="HIGH", category="process")
def kill_process(process_name: str = "", pid: int = 0) -> dict:
    """Kill a process by name or PID."""
    try:
        if not process_name and not pid:
            return {"status": "error", "message": "Provide process_name or pid"}

        killed = []
        if pid:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            proc.wait(timeout=5)
            killed.append({"pid": pid, "name": name})
        else:
            for proc in psutil.process_iter(["name", "pid"]):
                if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                        killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

        if not killed:
            return {"status": "error", "message": f"No matching process found for '{process_name or pid}'"}

        return {
            "status": "success",
            "data": {"killed_count": len(killed), "processes": killed},
            "message": f"Terminated {len(killed)} process(es)",
        }
    except psutil.NoSuchProcess:
        return {"status": "error", "message": f"Process PID {pid} no longer exists"}
    except psutil.AccessDenied:
        return {"status": "error", "message": "Access denied – run as administrator"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
