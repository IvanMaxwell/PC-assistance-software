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

# --- Performance Diagnostics ---

@registry.register(
    name="system.get_snapshot",
    description="Get system performance snapshot (CPU, Mem, Disk, Net) and Top 5 resource-consuming processes.",
    risk_level=ToolRisk.SAFE,
    required_params=[],
    semantic_aliases=[
        "Check system performance",
        "Open Task Manager",
        "Monitor system resources",
        "Why is my computer slow?",
        "Get process snapshot"
    ],
    sample_queries=[
        "Show me a system performance snapshot.",
        "What is using the most CPU right now?",
        "Open Task Manager and show top processes.",
        "Check current CPU, RAM, and Disk usage.",
        "Who is hogging all the memory?"
    ]
)
def get_system_snapshot() -> Dict[str, Any]:
    """Get comprehensive system snapshot (Global + Top Processes)."""
    # 1. Global Stats
    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net_io = psutil.net_io_counters()
    
    # 2. Process Stats (Iterate once)
    dataset = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            # cpu_percent might be 0 on first call if not cached, but we can't block too long
            # using interval=None is non-blocking
            p_cpu = p.info['cpu_percent'] 
            p_mem = p.info['memory_info'].rss / (1024 * 1024) # MB
            dataset.append({
                "pid": p.info['pid'],
                "name": p.info['name'],
                "cpu": p_cpu,
                "mem_mb": round(p_mem, 1),
                "status": p.info['status']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    # Sort
    top_cpu = sorted(dataset, key=lambda x: x['cpu'], reverse=True)[:5]
    top_mem = sorted(dataset, key=lambda x: x['mem_mb'], reverse=True)[:5]
    
    return {
        "global": {
            "cpu_total_percent": cpu_percent,
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "percent": mem.percent,
                "available_gb": round(mem.available / (1024**3), 2)
            },
            "disk_c": {
                 "free_gb": round(disk.free / (1024**3), 2),
                 "percent": disk.percent
            },
            "boot_time_net_sent_mb": round(net_io.bytes_sent / (1024**2), 1),
            "boot_time_net_recv_mb": round(net_io.bytes_recv / (1024**2), 1)
        },
        "top_processes": {
            "by_cpu": top_cpu,
            "by_memory": top_mem
        }
    }


# --- Network Port Diagnostics ---

@registry.register(
    name="net.port_list",
    description="List all open network ports and listening services/processes.",
    risk_level=ToolRisk.SAFE,
    required_params=[],
    semantic_aliases=[
        "List open ports",
        "Show listening ports",
        "Get network ports",
        "List network ports"
    ],
    sample_queries=[
        "What ports are currently open on my system?",
        "Show me all listening network ports.",
        "Are there any unauthorized services listening on the network?",
        "List all active TCP and UDP ports.",
        "Is anything running on port 8080?"
    ]
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
    required_params=[] , # log_type has a default ("System")
    semantic_aliases=[
        "Read event logs",
        "Check event logs",
        "Get event logs",
        "Read event logs"
    ],
    sample_queries=[
        "Did the system crash recently? Check the logs.",
        "Read the last 10 errors from the System event log.",
        "Are there any warnings in the Application logs?",
        "Show me recent Windows events"
    ]
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
    required_params=[],
    semantic_aliases=[
        "Check power plan",
        "Get power plan",
        "Read power plan",
        "Check power plan"
    ],
    sample_queries=[
        "What power plan is currently active?",
        "Show me the current power settings.",
        "Am I using Balanced or High Performance mode?",
        "Check my power plan configuration."
    ]
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
