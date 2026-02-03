"""
PC Automation Framework - Diagnostic Tools (Read-Only)
These tools gather system state without making changes.
"""
import os
import socket
import subprocess
import platform
from typing import Dict, List, Any

# Import registry to register tools
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tools.registry import registry, ToolRisk

import psutil # Added for new implementations


# --- FileSystem Diagnostics ---

@registry.register(
    name="fs.list_dir",
    description="List all files and folders in a specific directory path",
    risk_level=ToolRisk.SAFE,
    required_params=["path"]
)
def list_directory(path: str) -> List[Dict[str, Any]]:
    """List directory contents."""
    try:
        if not os.path.exists(path):
            return [{"error": f"Path not found: {path}"}]
            
        items = []
        with os.scandir(path) as it:
            for entry in it:
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else 0
                })
        return items[:50]  # Limit results
    except Exception as e:
        return [{"error": str(e)}]


@registry.register(
    name="fs.read_file_head",
    description="Read the first few lines of a text file (read logs, config files)",
    risk_level=ToolRisk.SAFE,
    required_params=["path"]
)
def read_file_head(path: str, lines: int = 10) -> Dict[str, Any]:
    """Read first N lines of a file."""
    try:
        content = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in range(lines):
                line = f.readline()
                if not line: break
                content.append(line.strip())
        return {"path": path, "content": content}
    except Exception as e:
        return {"error": str(e)}


@registry.register(
    name="fs.file_exists",
    description="Check if a specific file or directory exists at the path",
    risk_level=ToolRisk.SAFE,
    required_params=["path"]
)
def file_exists(path: str) -> Dict[str, bool]:
    """Check if file exists."""
    return {"exists": os.path.exists(path)}


# --- Network Diagnostics ---

@registry.register(
    name="net.get_config",
    description="Get network configuration (IP address, DNS settings, adapters)",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def get_network_config() -> Dict[str, Any]:
    """Get IP and interface info."""
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return {
            "hostname": hostname,
            "ip_address": ip,
            "interfaces": psutil.net_if_addrs()
        }
    except Exception as e:
        return {"error": str(e)}


@registry.register(
    name="net.check_connection",
    description="Check my internet connection status. Verify if I am online by pinging external server.",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def check_connectivity(host: str = "8.8.8.8") -> Dict[str, Any]:
    """Ping a host to check connection."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=2)
        return {
            "connected": result.returncode == 0,
            "target": host
        }
    except subprocess.TimeoutExpired:
        return {"connected": False, "error": "Timeout"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


# --- Process/System Diagnostics ---

@registry.register(
    name="proc.list",
    description="List all currently running processes and their PIDs",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def list_processes(limit: int = 20) -> List[Dict[str, Any]]:
    """List top N processes."""
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        procs.append(proc.info)
        if len(procs) >= limit:
            break
    return procs


@registry.register(
    name="sys.get_info",
    description="Get system information (OS, CPU, RAM)",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version()
    }
