"""
File diagnostic tools – list, search, and inspect files.
All SAFE / read-only.
"""

from pathlib import Path
from typing import Optional, List
import os
import time

from tools.registry import registry


@registry.register(risk_level="SAFE", category="files")
def list_files(directory: str, show_hidden: bool = False, limit: int = 50) -> dict:
    """List files and folders in a directory."""
    try:
        path = Path(directory).expanduser().resolve()
        if not path.exists():
            return {"status": "error", "message": f"Directory '{directory}' not found"}
        if not path.is_dir():
            return {"status": "error", "message": f"'{directory}' is not a directory"}

        items = []
        count = 0
        for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
            if not show_hidden and entry.name.startswith("."):
                continue
            if count >= limit:
                break
            info = {
                "name": entry.name,
                "type": "file" if entry.is_file() else "dir",
            }
            if entry.is_file():
                stat = entry.stat()
                info["size_bytes"] = stat.st_size
                info["size_human"] = _human_size(stat.st_size)
                info["modified"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
            items.append(info)
            count += 1

        return {
            "status": "success",
            "data": {
                "directory": str(path),
                "total_items": count,
                "items": items,
            },
        }
    except PermissionError:
        return {"status": "error", "message": "Permission denied"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="files")
def search_files(
    pattern: str = "*",
    search_path: str = "~",
    max_results: int = 20,
    file_extension: Optional[str] = None,
    query: Optional[str] = None,
) -> dict:
    """Search for files matching a glob pattern in search_path.

    Args:
        pattern: Glob pattern to match (e.g. "*.txt", "report*"). Defaults to "*".
        search_path: Directory to search in. Defaults to home directory.
        max_results: Maximum number of results to return.
        file_extension: Optional file extension filter (e.g. ".pdf" or "pdf").
                        When provided, overrides pattern with "*.{extension}".
        query: Alias for pattern — accepts a filename or glob string.
               Ignored if file_extension is provided.
    """
    try:
        # Priority: file_extension > query > pattern
        if file_extension:
            ext = file_extension.lstrip(".")
            pattern = f"*.{ext}"
        elif query:
            pattern = query  # treat query as a glob/filename pattern

        root = Path(search_path).expanduser().resolve()
        if not root.exists():
            return {"status": "error", "message": f"Path '{search_path}' not found"}

        matches = []
        for match in root.rglob(pattern):
            if len(matches) >= max_results:
                break
            try:
                stat = match.stat()
                matches.append({
                    "path": str(match),
                    "name": match.name,
                    "size_human": _human_size(stat.st_size) if match.is_file() else "dir",
                    "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                })
            except (PermissionError, OSError):
                continue

        return {
            "status": "success",
            "data": {
                "pattern": pattern,
                "search_path": str(root),
                "result_count": len(matches),
                "results": matches,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="files")
def get_file_info(file_path: str) -> dict:
    """Get detailed info for a single file."""
    try:
        p = Path(file_path).expanduser().resolve()
        if not p.exists():
            return {"status": "error", "message": f"File '{file_path}' not found"}

        stat = p.stat()
        return {
            "status": "success",
            "data": {
                "name": p.name,
                "path": str(p),
                "type": "file" if p.is_file() else "dir",
                "size_bytes": stat.st_size,
                "size_human": _human_size(stat.st_size),
                "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_ctime)),
                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                "extension": p.suffix,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── helpers ──────────────────────────────────────────────────────────

def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"
