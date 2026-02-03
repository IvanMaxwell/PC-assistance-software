"""
PC Automation Framework - Advanced Diagnostic Tools
Requires: psutil, pywin32
"""
import psutil
import subprocess
from typing import Dict, List, Any, Optional
from tools.registry import registry, ToolRisk
try:
    import win32evtlog # type: ignore
except ImportError:
    win32evtlog = None


# --- Performance Diagnostics ---

@registry.register(
    name="perf.cpu_mem_snapshot",
    description="Check system performance. Get CPU load, memory usage, and free disk space.",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def get_performance_snapshot() -> Dict[str, Any]:
    """Get current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent
        },
        "disk_c": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        }
    }


# --- Network Port Diagnostics ---

@registry.register(
    name="net.port_list",
    description="List all open network ports and listening services/processes.",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def list_open_ports(limit: int = 20) -> List[Dict[str, Any]]:
    """List open network ports."""
    results = []
    for conn in psutil.net_connections(kind='inet'):
        if conn.status == 'LISTEN':
            try:
                proc = psutil.Process(conn.pid)
                proc_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = "Unknown"
            
            results.append({
                "port": conn.laddr.port,
                "pid": conn.pid,
                "process": proc_name,
                "type": "TCP" if conn.type == 1 else "UDP"
            })
            if len(results) >= limit:
                break
    return results


# --- Windows Event Log ---

@registry.register(
    name="eventlog.read",
    description="Read recent Windows Event Logs to find system errors or crashes.",
    risk_level=ToolRisk.SAFE,
    required_params=[]  # log_type has a default ("System")
)
def read_event_log(log_type: str = "System", num_records: int = 10) -> List[Dict[str, Any]]:
    """
    Read Windows Event Logs.
    log_type: 'System', 'Application', or 'Security'
    """
    if not win32evtlog:
        return [{"error": "pywin32 not installed"}]
        
    server = 'localhost'
    log_type = log_type.capitalize()
    if log_type not in ["System", "Application", "Security"]:
        return [{"error": "Invalid log_type. Must be System, Application, or Security"}]

    try:
        hand = win32evtlog.OpenEventLog(server, log_type)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        total = 0
        events = []
        
        while True:
            raw_events = win32evtlog.ReadEventLog(hand, flags, 0)
            if not raw_events:
                break
            for event in raw_events:
                events.append({
                    "time": event.TimeGenerated.isoformat(),
                    "source": event.SourceName,
                    "event_id": event.EventID & 0xFFFF,
                    "type": event.EventType,
                    "message": " ".join(event.StringInserts) if event.StringInserts else ""
                })
                total += 1
                if total >= num_records:
                    break
            if total >= num_records:
                break
        win32evtlog.CloseEventLog(hand)
        return events
    except Exception as e:
        return [{"error": str(e)}]


# --- Power Plan ---

@registry.register(
    name="power.plan_query",
    description="Check current power plan (Balanced, High Performance, Power Saver).",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def query_power_plan() -> Dict[str, str]:
    """Query active power plan using powercfg."""
    try:
        output = subprocess.check_output("powercfg /getactivescheme", shell=True).decode()
        # Output format: "Power Scheme GUID: <GUID>  (Balanced)"
        parts = output.split("(")
        if len(parts) > 1:
            name = parts[1].replace(")", "").strip()
            guid = parts[0].split(":")[1].strip()
            return {"name": name, "guid": guid}
        return {"raw_output": output.strip()}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}
