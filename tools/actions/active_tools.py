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
    required_params=[],
    semantic_aliases=[
        "Clear DNS cache",
        "Refresh network resolution",
        "Reset DNS records",
        "Flush internet cache"
    ],
    sample_queries=[
        "Flush my DNS cache.",
        "I can't reach the site, try clearing DNS.",
        "Run ipconfig /flushdns equivalent.",
        "Reset the DNS resolver."
    ]
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
    required_params=["adapter_name"],
    semantic_aliases=[
        "Restart network interface",
        "Cycle network adapter",
        "Disable and enable Wi-Fi",
        "Reset ethernet connection"
    ],
    sample_queries=[
        "Reset the 'Wi-Fi' adapter.",
        "My internet is buggy, restart the network card.",
        "Disable and re-enable the Ethernet connection.",
        "Cycle the network interface to fix connection issues."
    ]
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
    required_params=["pid"],
    semantic_aliases=[
        "Terminate process",
        "End program task",
        "Stop running app",
        "Force close process"
    ],
    sample_queries=[
        "Kill process with PID 1234.",
        "Force close the stuck Notepad application.",
        "Terminate the suspicious background task.",
        "End the process that is using too much CPU."
    ]
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
    required_params=[],
    semantic_aliases=[
        "View Windows services",
        "Show installed services",
        "List service status",
        "Check background services"
    ],
    sample_queries=[
        "List all installed Windows services.",
        "Show me the status of all services.",
        "What services are currently stopped?",
        "Get a list of services running on the machine."
    ]
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
    required_params=["service_name"],
    semantic_aliases=[
        "Check specific service",
        "Get service details",
        "Inspect service state",
        "Query service info"
    ],
    sample_queries=[
        "Is the 'Spooler' service running?",
        "Check the status of the Windows Update service.",
        "Get details for the 'wuauserv' service.",
        "Find out if the firewall service is active."
    ]
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
    required_params=["service_name"],
    semantic_aliases=[
        "Halt Windows service",
        "Stop background service",
        "Disable service execution",
        "Turn off service"
    ],
    sample_queries=[
        "Stop the 'Print Spooler' service.",
        "Turn off the 'wuauserv' service temporarily.",
        "Halt the background update service.",
        "Execute a stop command for the SQL Server service."
    ]
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
    required_params=["service_name"],
    semantic_aliases=[
        "Launch Windows service",
        "Enable background service",
        "Resume service execution",
        "Turn on service"
    ],
    sample_queries=[
        "Start the 'w32time' service.",
        "Turn on the Windows Audio service.",
        "Resume the stopped 'Spooler' service.",
        "Enable the firewall service."
    ]
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
    required_params=["path"],
    semantic_aliases=[
        "Remove file",
        "Delete item",
        "Erase document",
        "Clean up directory"
    ],
    sample_queries=[
        r"Delete the file C:\temp\old_log.txt.",
        r"Remove the empty folder C:\Users\Home\EmptyDir.",
        "Erase the installer.exe from Downloads.",
        "Clean up the temp file I just created."
    ]
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
    required_params=[],
    semantic_aliases=[
        "Clear temporary files",
        "Free up disk space",
        "Run system cleanup",
        "Remove junk files"
    ],
    sample_queries=[
        "Run Disk Cleanup to free up space.",
        "Clear out temporary system files.",
        "My disk is full, run a cleanup.",
        "Execute maintenance to remove junk files."
    ]
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
