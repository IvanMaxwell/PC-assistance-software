"""
File action tools – organize, clean up, and batch-operate on files.
Risk: MEDIUM (moves/deletes files).
"""

from pathlib import Path
from typing import List, Optional
import shutil
import time

from tools.registry import registry


# ── Type map for organize_by_type ────────────────────────────────────

_TYPE_MAP = {
    ".pdf": "Documents", ".docx": "Documents", ".doc": "Documents",
    ".txt": "Documents", ".xlsx": "Documents", ".xls": "Documents",
    ".pptx": "Documents", ".csv": "Documents", ".rtf": "Documents",
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
    ".gif": "Images", ".bmp": "Images", ".svg": "Images", ".webp": "Images",
    ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos",
    ".mov": "Videos", ".wmv": "Videos",
    ".mp3": "Music", ".wav": "Music", ".flac": "Music", ".aac": "Music",
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
    ".tar": "Archives", ".gz": "Archives",
    ".exe": "Installers", ".msi": "Installers",
    ".py": "Code", ".js": "Code", ".html": "Code", ".css": "Code",
    ".java": "Code", ".cpp": "Code", ".c": "Code",
}


@registry.register(risk_level="MEDIUM", category="files")
def organize_downloads(method: str = "by_type", dry_run: bool = False) -> dict:
    """Organize downloads folder by type or date."""
    try:
        if method not in ("by_type", "by_date"):
            return {"status": "error", "message": f"Invalid method '{method}'. Use 'by_type' or 'by_date'"}

        downloads = Path.home() / "Downloads"
        if not downloads.exists():
            return {"status": "error", "message": "Downloads folder not found"}

        files = [f for f in downloads.iterdir() if f.is_file()]
        if not files:
            return {"status": "success", "data": {"moved": 0, "message": "No files to organize"}}

        if method == "by_type":
            grouped = _group_by_type(files)
        else:
            grouped = _group_by_date(files)

        if dry_run:
            preview = {folder: [f.name for f in flist] for folder, flist in grouped.items()}
            return {
                "status": "success",
                "data": {
                    "would_move": sum(len(v) for v in grouped.values()),
                    "would_create_folders": len(grouped),
                    "preview": preview,
                },
            }

        moved, created = 0, 0
        for folder, flist in grouped.items():
            target = downloads / folder
            if not target.exists():
                target.mkdir()
                created += 1
            for f in flist:
                dest = target / f.name
                # Handle name collisions
                if dest.exists():
                    dest = target / f"{f.stem}_{int(time.time())}{f.suffix}"
                f.rename(dest)
                moved += 1

        return {
            "status": "success",
            "data": {"moved": moved, "created_folders": created, "method": method},
            "message": f"Organized {moved} files into {created} folders",
        }
    except PermissionError:
        return {"status": "error", "message": "Permission denied. Run as administrator."}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {e}"}


@registry.register(risk_level="MEDIUM", category="files")
def find_large_files(directory: str = "~", min_size_mb: int = 100, limit: int = 20) -> dict:
    """Find files larger than min_size_mb in a directory tree."""
    try:
        root = Path(directory).expanduser().resolve()
        if not root.exists():
            return {"status": "error", "message": f"Path '{directory}' not found"}

        threshold = min_size_mb * 1024 * 1024
        large = []
        for entry in root.rglob("*"):
            if len(large) >= limit:
                break
            try:
                if entry.is_file() and entry.stat().st_size >= threshold:
                    large.append({
                        "path": str(entry),
                        "name": entry.name,
                        "size_mb": round(entry.stat().st_size / (1024 ** 2), 2),
                    })
            except (PermissionError, OSError):
                continue

        large.sort(key=lambda x: x["size_mb"], reverse=True)
        return {
            "status": "success",
            "data": {"count": len(large), "min_size_mb": min_size_mb, "files": large},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="MEDIUM", category="files")
def clear_temp_files(dry_run: bool = True) -> dict:
    """Clear Windows temp files."""
    try:
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        removed, failed, total_bytes = 0, 0, 0

        items = list(temp_dir.iterdir())
        results = []

        for item in items:
            try:
                size = item.stat().st_size if item.is_file() else 0
                if dry_run:
                    results.append({"name": item.name, "size_mb": round(size / (1024**2), 2)})
                    total_bytes += size
                    removed += 1
                else:
                    if item.is_file():
                        total_bytes += size
                        item.unlink()
                        removed += 1
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                        removed += 1
            except (PermissionError, OSError):
                failed += 1

        return {
            "status": "success",
            "data": {
                "dry_run": dry_run,
                "removed": removed,
                "failed": failed,
                "freed_mb": round(total_bytes / (1024**2), 2),
                "preview": results[:20] if dry_run else [],
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── helpers ──────────────────────────────────────────────────────────

def _group_by_type(files: List[Path]) -> dict:
    grouped = {}
    for f in files:
        folder = _TYPE_MAP.get(f.suffix.lower(), "Other")
        grouped.setdefault(folder, []).append(f)
    return grouped


def _group_by_date(files: List[Path]) -> dict:
    grouped = {}
    for f in files:
        mtime = f.stat().st_mtime
        folder = time.strftime("%Y-%m", time.localtime(mtime))
        grouped.setdefault(folder, []).append(f)
    return grouped
