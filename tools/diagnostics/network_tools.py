"""
Network diagnostic tools – connectivity checks and config.
All SAFE / read-only.
"""

import socket
import time
from typing import Optional

from tools.registry import registry


@registry.register(risk_level="SAFE", category="network")
def check_internet_connection(host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> dict:
    """Check if internet connection is available by connecting to a host."""
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        latency_ms = round((time.time() - start) * 1000, 2)
        sock.close()
        return {
            "status": "success",
            "data": {
                "connected": True,
                "host": host,
                "latency_ms": latency_ms,
            },
        }
    except OSError:
        return {
            "status": "success",
            "data": {"connected": False, "host": host, "latency_ms": None},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="network")
def get_network_config() -> dict:
    """Get network interface information."""
    try:
        import psutil

        interfaces = {}
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface, addr_list in addrs.items():
            iface_info = {"addresses": [], "is_up": False}
            if iface in stats:
                iface_info["is_up"] = stats[iface].isup
                iface_info["speed_mbps"] = stats[iface].speed

            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    iface_info["addresses"].append({
                        "type": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask,
                    })
            if iface_info["addresses"]:
                interfaces[iface] = iface_info

        hostname = socket.gethostname()
        return {
            "status": "success",
            "data": {
                "hostname": hostname,
                "interfaces": interfaces,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
