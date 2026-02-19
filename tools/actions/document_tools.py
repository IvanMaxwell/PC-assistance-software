"""
Document editing tools (class-based).

Provides tools for reading, writing, appending, and editing text files.
All MEDIUM risk — modifies files on disk.
"""

import os
import inspect
from pathlib import Path
from typing import Optional

from tools.registry import registry, ToolMeta


def _extract_params(method):
    sig = inspect.signature(method)
    params = []
    for pname, param in sig.parameters.items():
        if pname == "self":
            continue
        ptype = "string"
        if param.annotation != inspect.Parameter.empty:
            ptype = getattr(param.annotation, "__name__", str(param.annotation))
        params.append({
            "name": pname,
            "type": ptype,
            "required": param.default is inspect.Parameter.empty,
            "default": None if param.default is inspect.Parameter.empty else param.default,
        })
    return params


class DocumentTools:
    """
    Class-based tool group for reading and editing text documents.
    """

    def __init__(self):
        self._register()

    def _register(self):
        tool_defs = [
            ("read_text_file",    "SAFE",   "files"),
            ("write_text_file",   "MEDIUM", "files"),
            ("append_to_file",    "MEDIUM", "files"),
            ("replace_in_file",   "MEDIUM", "files"),
            ("get_file_preview",  "SAFE",   "files"),
            ("delete_file",       "HIGH",   "files"),
            ("create_directory",  "MEDIUM", "files"),
            ("copy_file",         "MEDIUM", "files"),
            ("move_file",         "MEDIUM", "files"),
        ]
        for name, risk, category in tool_defs:
            method = getattr(self, name)
            doc = (method.__doc__ or "").strip().split("\n")[0]
            meta = ToolMeta(
                name=name,
                func=method,
                risk_level=risk,
                category=category,
                description=doc,
                parameters=_extract_params(method),
            )
            registry._tools[name] = meta

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_text_file(self, file_path: str, max_chars: int = 10000) -> dict:
        """Read a text file and return its content."""
        try:
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            text = p.read_text(encoding="utf-8", errors="replace")
            return {
                "status": "success",
                "data": {
                    "file": str(p),
                    "content": text[:max_chars],
                    "total_chars": len(text),
                    "truncated": len(text) > max_chars,
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_file_preview(self, file_path: str, lines: int = 20) -> dict:
        """Return the first N lines of a file."""
        try:
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            all_lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            preview = "\n".join(all_lines[:lines])
            return {
                "status": "success",
                "data": {
                    "file": str(p),
                    "preview": preview,
                    "lines_shown": min(lines, len(all_lines)),
                    "total_lines": len(all_lines),
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Write / Edit
    # ------------------------------------------------------------------

    def write_text_file(self, file_path: str, content: str) -> dict:
        """Write (overwrite) a text file with the given content."""
        try:
            p = Path(file_path).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {
                "status": "success",
                "data": {"file": str(p), "bytes_written": len(content.encode("utf-8"))}
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def append_to_file(self, file_path: str, content: str) -> dict:
        """Append text to the end of a file (creates it if it doesn't exist)."""
        try:
            p = Path(file_path).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
            return {
                "status": "success",
                "data": {"file": str(p), "bytes_appended": len(content.encode("utf-8"))}
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def replace_in_file(self, file_path: str, find: str, replace: str) -> dict:
        """Find and replace all occurrences of a string in a text file."""
        try:
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            text = p.read_text(encoding="utf-8", errors="replace")
            count = text.count(find)
            if count == 0:
                return {"status": "success", "data": {"file": str(p), "replacements": 0, "message": "String not found"}}
            new_text = text.replace(find, replace)
            p.write_text(new_text, encoding="utf-8")
            return {
                "status": "success",
                "data": {"file": str(p), "replacements": count}
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # File Operations
    # ------------------------------------------------------------------

    def delete_file(self, file_path: str) -> dict:
        """Permanently delete a file from disk."""
        try:
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            if p.is_dir():
                return {"status": "error", "message": "Path is a directory, not a file"}
            p.unlink()
            return {"status": "success", "data": {"deleted": str(p)}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_directory(self, dir_path: str) -> dict:
        """Create a directory (and any missing parents)."""
        try:
            p = Path(dir_path).expanduser().resolve()
            p.mkdir(parents=True, exist_ok=True)
            return {"status": "success", "data": {"directory": str(p)}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def copy_file(self, source_path: str, dest_path: str) -> dict:
        """Copy a file from source to destination."""
        try:
            import shutil
            src = Path(source_path).expanduser().resolve()
            dst = Path(dest_path).expanduser().resolve()
            if not src.exists():
                return {"status": "error", "message": f"Source not found: {source_path}"}
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            return {"status": "success", "data": {"source": str(src), "destination": str(dst)}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def move_file(self, source_path: str, dest_path: str) -> dict:
        """Move or rename a file."""
        try:
            import shutil
            src = Path(source_path).expanduser().resolve()
            dst = Path(dest_path).expanduser().resolve()
            if not src.exists():
                return {"status": "error", "message": f"Source not found: {source_path}"}
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return {"status": "success", "data": {"moved_from": str(src), "moved_to": str(dst)}}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Module-level singleton — instantiation triggers registration
document_tools = DocumentTools()
