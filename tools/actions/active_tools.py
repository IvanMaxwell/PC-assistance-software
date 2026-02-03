"""
PC Automation Framework - Active Tools (System Modification)
WARNING: These tools make changes to the system. Use with caution.
"""
import subprocess
import os
import psutil
from typing import Dict, List, Any, Optional
from tools.registry import registry, ToolRisk


# --- Network Actions ---

@registry.register(
    name="net.flush_dns",
    description="Flush DNS resolver cache",
    risk_level=ToolRisk.MEDIUM,
    required_params=[]
)
def flush_dns() -> Dict[str, Any]:
    """Flush DNS cache using ipconfig."""
    try:
        result = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="net.reset_adapter",
    description="Disable and re-enable a network adapter",
    risk_level=ToolRisk.HIGH,
    required_params=["adapter_name"]
)
def reset_network_adapter(adapter_name: str) -> Dict[str, Any]:
    """
    Reset a network adapter (requires admin).
    adapter_name: e.g., 'Wi-Fi', 'Ethernet'
    """
    try:
        # Disable
        subprocess.run(
            ["netsh", "interface", "set", "interface", adapter_name, "disabled"],
            capture_output=True,
            timeout=5
        )
        # Enable
        result = subprocess.run(
            ["netsh", "interface", "set", "interface", adapter_name, "enabled"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return {
            "success": result.returncode == 0,
            "adapter": adapter_name,
            "message": "Adapter reset"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Process Management ---

@registry.register(
    name="proc.kill",
    description="Terminate a process by PID",
    risk_level=ToolRisk.HIGH,
    required_params=["pid"]
)
def kill_process(pid: int) -> Dict[str, Any]:
    """Kill a process by its PID."""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        proc.terminate()
        proc.wait(timeout=5)
        return {
            "success": True,
            "pid": pid,
            "process_name": proc_name,
            "message": f"Process {proc_name} ({pid}) terminated"
        }
    except psutil.NoSuchProcess:
        return {"success": False, "error": f"Process {pid} does not exist"}
    except psutil.AccessDenied:
        return {"success": False, "error": f"Access denied to kill process {pid}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Service Management ---

@registry.register(
    name="service.list",
    description="List Windows services and their status",
    risk_level=ToolRisk.SAFE,
    required_params=[]
)
def list_services(limit: int = 50) -> List[Dict[str, Any]]:
    """List Windows services using sc query."""
    try:
        result = subprocess.run(
            ["sc", "query", "type=", "service", "state=", "all"],
            capture_output=True,
            text=True,
            timeout=10
        )
        services = []
        current_service = {}
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith("SERVICE_NAME:"):
                if current_service:
                    services.append(current_service)
                current_service = {"name": line.split(":", 1)[1].strip()}
            elif line.startswith("DISPLAY_NAME:"):
                current_service["display_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("STATE"):
                parts = line.split()
                if len(parts) >= 4:
                    current_service["state"] = parts[3]
            
            if len(services) >= limit:
                break
        
        if current_service and len(services) < limit:
            services.append(current_service)
        
        return services
    except Exception as e:
        return [{"error": str(e)}]


@registry.register(
    name="service.query",
    description="Get detailed status of a specific service",
    risk_level=ToolRisk.SAFE,
    required_params=["service_name"]
)
def query_service(service_name: str) -> Dict[str, Any]:
    """Query a specific service status."""
    try:
        result = subprocess.run(
            ["sc", "query", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        info = {"name": service_name}
        for line in result.stdout.split('\n'):
            line = line.strip()
            if "STATE" in line:
                parts = line.split()
                if len(parts) >= 4:
                    info["state"] = parts[3]
            elif "TYPE" in line:
                info["type"] = line.split(":", 1)[1].strip()
        
        return info
    except Exception as e:
        return {"error": str(e)}


@registry.register(
    name="service.stop",
    description="Stop a Windows service (requires admin)",
    risk_level=ToolRisk.HIGH,
    required_params=["service_name"]
)
def stop_service(service_name: str) -> Dict[str, Any]:
    """Stop a Windows service."""
    try:
        result = subprocess.run(
            ["net", "stop", service_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "service": service_name,
            "message": result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="service.start",
    description="Start a Windows service (requires admin)",
    risk_level=ToolRisk.HIGH,
    required_params=["service_name"]
)
def start_service(service_name: str) -> Dict[str, Any]:
    """Start a Windows service."""
    try:
        result = subprocess.run(
            ["net", "start", service_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "service": service_name,
            "message": result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Filesystem Actions ---

@registry.register(
    name="fs.delete_file",
    description="Delete a file or empty directory",
    risk_level=ToolRisk.HIGH,
    required_params=["path"]
)
def delete_file(path: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Delete a file.
    confirm: Must be True to actually delete (safety check)
    """
    if not confirm:
        return {
            "success": False,
            "error": "Deletion not confirmed. Set confirm=True to proceed."
        }
    
    try:
        if os.path.isfile(path):
            os.remove(path)
            return {"success": True, "path": path, "message": "File deleted"}
        elif os.path.isdir(path):
            os.rmdir(path)  # Only works on empty dirs
            return {"success": True, "path": path, "message": "Empty directory deleted"}
        else:
            return {"success": False, "error": f"Path does not exist: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="disk.cleanup",
    description="Run Windows Disk Cleanup for temp files",
    risk_level=ToolRisk.MEDIUM,
    required_params=[]
)
def run_disk_cleanup() -> Dict[str, Any]:
    """Run cleanmgr (Windows Disk Cleanup) silently."""
    try:
        # Run cleanmgr with /sagerun to execute saved settings
        result = subprocess.run(
            ["cleanmgr", "/sagerun:1"],
            capture_output=True,
            timeout=60
        )
        return {
            "success": True,
            "message": "Disk cleanup initiated (runs in background)"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
