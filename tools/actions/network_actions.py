"""
Network action tools – flush DNS, reset adapters.
Risk: MEDIUM (temporary network disruption).
"""

import subprocess
import platform

from tools.registry import registry


@registry.register(risk_level="MEDIUM", category="network")
def flush_dns() -> dict:
    """Flush the DNS resolver cache (Windows only)."""
    try:
        if platform.system() != "Windows":
            return {"status": "error", "message": "This tool only supports Windows"}

        result = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True, text=True, timeout=10,
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "data": {"output": result.stdout.strip()},
                "message": "DNS cache flushed successfully",
            }
        return {"status": "error", "message": result.stderr.strip() or "Failed to flush DNS"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
