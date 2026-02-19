"""
PC Automation Framework – FastAPI Backend
Serves the frontend and provides REST API endpoints.
"""

import sys
import os
import asyncio
import time
import json
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from tools import discover_tools
discover_tools()

from tools.registry import registry
from core.orchestrator import Orchestrator
from core.config import config, SafetyMode
from core.logger import logger

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(title="PC Automation Framework", version="2.0")

# Global orchestrator (reused across requests)
_orchestrator: Optional[Orchestrator] = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        # Use AUTONOMOUS mode for the web UI (no CLI prompts)
        config.safety_mode = SafetyMode.AUTONOMOUS
        _orchestrator = Orchestrator(display=None)
    return _orchestrator


# ── Models ───────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    command: str


# ── API Endpoints ────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/status")
@app.get("/api/status/") # Trailing slash tolerance
async def get_status():
    """Return system and agent status."""
    try:
        # Quick system metrics
        import psutil # Imported here to avoid global import if not used
        orchestrator = _get_orchestrator() # Get orchestrator instance

        stats = {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_percent": psutil.disk_usage('C:').percent,
                "disk_free_gb": round(psutil.disk_usage('C:').free / (1024**3), 2),
            },
            "agents": orchestrator.get_status(),
            "tool_count": len(registry.list_names())
        }
        return stats
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"error": str(e)}


@app.get("/api/tools")
@app.get("/api/tools/") # Trailing slash tolerance
async def get_tools():
    """List all available tools."""
    tools = registry.list_tools()
    return {"tools": tools, "count": len(tools)}


@app.get("/api/similarity")
@app.get("/api/similarity/") # Trailing slash tolerance
async def similarity(query: str):
    """Return semantic similarity scores for a query."""
    try:
        from core.router import get_router
        router = get_router()
        if router:
            scores = router.get_similarity_scores(query, top_k=5)
            return {"query": query, "matches": scores}
        return {"query": query, "matches": [], "message": "Router unavailable"}
    except Exception as e:
        return {"query": query, "matches": [], "error": str(e)}


@app.post("/api/execute")
async def execute(req: ExecuteRequest):
    """Execute a user command through the orchestrator."""
    orch = _get_orchestrator()
    start = time.time()

    # We collect events as the orchestrator runs
    events = []

    class WebDisplay:
        """Minimal display adapter that captures events for the API response."""

        def show_state_transition(self, from_s, to_s):
            events.append({"type": "state", "from": from_s, "to": to_s})

        def show_cm_response(self, resp):
            events.append({"type": "cm_response", "reply": resp.get("reply", ""),
                           "explanation": resp.get("explanation", "")})

        def show_router_result(self, query, tool, score, hit):
            events.append({"type": "router", "query": query, "tool": tool,
                           "score": score, "hit": hit})

        def show_plan(self, plan):
            events.append({"type": "plan", "plan": plan})

        def show_confidence(self, score):
            events.append({"type": "confidence", "score": score})

        def show_risk_assessment(self, assessment):
            events.append({"type": "risk_assessment", **assessment})

        def show_step_result(self, step_id, tool, status, result=None, error=None):
            events.append({"type": "step_result", "step_id": step_id,
                           "tool": tool, "status": status,
                           "result": _safe_serialize(result),
                           "error": error})

        def show_drift_alert(self, drift):
            events.append({"type": "drift", **drift})

        def show_final_summary(self, summary):
            events.append({"type": "summary", "text": summary})

        def ask_permission(self, step_id, tool_name, risk, args):
            return True  # Auto-approve in web mode

    web_display = WebDisplay()
    orch._display = web_display

    # Run in thread to not block event loop
    try:
        results = await asyncio.to_thread(orch.run, req.command)
    except Exception as e:
        results = [{"status": "error", "error": str(e)}]

    elapsed = round(time.time() - start, 2)

    return {
        "command": req.command,
        "elapsed_seconds": elapsed,
        "events": events,
        "results": _safe_serialize(results),
        "summary": orch.context.summary,
        "confidence": orch.context.confidence_score,
        "cm_response": orch.context.cm_response,
        "cs_assessment": orch.context.cs_assessment,
    }


@app.get("/api/history")
async def history():
    """Return execution history from memory."""
    orch = _get_orchestrator()
    if orch._memory:
        entries = orch._memory.short_term.get_recent(20)
        return {
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "category": e.category,
                    "request": e.content.get("request", ""),
                    "confidence": e.content.get("confidence", 0),
                    "results": _safe_serialize(e.content.get("results", [])),
                }
                for e in entries
            ]
        }
    return {"entries": []}


# ── Helpers ──────────────────────────────────────────────────────────

def _safe_serialize(obj):
    """Make an object JSON-serializable."""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return json.loads(json.dumps(obj, default=str))


# ── Static Files (Frontend) ─────────────────────────────────────────

frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PC Automation Framework Server...")
    print("   Dashboard: http://localhost:8000")
    print("   API Docs:  http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
