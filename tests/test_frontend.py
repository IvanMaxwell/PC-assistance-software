"""
PC Automation Framework – Frontend & API Connectivity Tests
Run:  python tests/test_frontend.py

Starts the FastAPI server on a free port, then tests every endpoint
and verifies the frontend HTML/CSS/JS is served correctly.
"""

import sys
import os
import time
import json
import threading
import urllib.request
import urllib.error

# ── Setup path ───────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

# ── Helpers ──────────────────────────────────────────────────────────
PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def api_get(path):
    """GET a JSON endpoint."""
    url = f"http://127.0.0.1:{PORT}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def api_post(path, data):
    """POST JSON to an endpoint."""
    url = f"http://127.0.0.1:{PORT}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def http_get_text(path):
    """GET raw text (for HTML/CSS/JS)."""
    url = f"http://127.0.0.1:{PORT}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode(), resp.status


# ══════════════════════════════════════════════════════════════════════
#  0. Start Server
# ══════════════════════════════════════════════════════════════════════

section("0. Starting FastAPI Server")

PORT = 18765  # Use a high port to avoid conflicts

def run_server():
    import uvicorn
    # Import server, which triggers discover_tools
    from server import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for server to start
server_up = False
for i in range(30):
    time.sleep(1)
    try:
        api_get("/api/health")
        server_up = True
        break
    except Exception:
        pass

check("server started", server_up, "Timed out waiting for server")
if not server_up:
    print("\n  ❌ Cannot continue — server did not start.")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════
#  1. Health Endpoint
# ══════════════════════════════════════════════════════════════════════

section("1. GET /api/health")

try:
    data = api_get("/api/health")
    check("returns JSON", isinstance(data, dict))
    check("has 'status'", "status" in data)
    check("status is ok", data["status"] == "ok")
    check("has timestamp", "timestamp" in data)
except Exception as e:
    check("/api/health", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  2. Status Endpoint
# ══════════════════════════════════════════════════════════════════════

section("2. GET /api/status")

try:
    data = api_get("/api/status")
    check("returns JSON", isinstance(data, dict))
    check("has 'system'", "system" in data)
    check("has 'agents'", "agents" in data)
    check("has 'tool_count'", "tool_count" in data)

    sys_data = data["system"]
    check("system has cpu_percent", "cpu_percent" in sys_data)
    check("system has memory_percent", "memory_percent" in sys_data)
    check("system has disk_percent", "disk_percent" in sys_data)

    agents = data["agents"]
    check("agents has cm_agent", "cm_agent" in agents)
    check("agents has cs_agent", "cs_agent" in agents)
    check("agents has orchestrator", "orchestrator" in agents)

    check(f"tool_count > 0: {data['tool_count']}", data["tool_count"] > 0)
except Exception as e:
    check("/api/status", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  3. Tools Endpoint
# ══════════════════════════════════════════════════════════════════════

section("3. GET /api/tools")

try:
    data = api_get("/api/tools")
    check("returns JSON", isinstance(data, dict))
    check("has 'tools' list", isinstance(data.get("tools"), list))
    check("has 'count'", "count" in data)
    check(f"count > 0: {data['count']}", data["count"] > 0)

    if data["tools"]:
        t = data["tools"][0]
        check("tool has 'name'", "name" in t)
        check("tool has 'risk'", "risk" in t)
        check("tool has 'category'", "category" in t)
        check("tool has 'description'", "description" in t)
        check("tool has 'parameters'", "parameters" in t)

    # Check we have the expected categories
    cats = set(t["category"] for t in data["tools"])
    print(f"     Categories: {cats}")
    check("multiple categories", len(cats) > 1)

    # Check risk levels
    risks = set(t["risk"] for t in data["tools"])
    print(f"     Risk levels: {risks}")
except Exception as e:
    check("/api/tools", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  4. Execute Endpoint
# ══════════════════════════════════════════════════════════════════════

section("4. POST /api/execute")

try:
    data = api_post("/api/execute", {"command": "Check my CPU usage"})
    check("returns JSON", isinstance(data, dict))
    check("has 'command'", data.get("command") == "Check my CPU usage")
    check("has 'elapsed_seconds'", "elapsed_seconds" in data)
    check("has 'events'", isinstance(data.get("events"), list))
    check("has 'results'", "results" in data)
    check("has 'summary'", "summary" in data)
    check("has 'confidence'", "confidence" in data)
    check("has 'cm_response'", "cm_response" in data)

    # Check events
    events = data["events"]
    event_types = [e["type"] for e in events]
    print(f"     Event types: {event_types}")
    check("has state events", "state" in event_types)

    # Check cm_response
    cm = data.get("cm_response")
    if cm:
        check("cm_response has reply", "reply" in cm)
        print(f"     CM reply: {cm.get('reply', '')[:60]}")

    # Check summary
    if data.get("summary"):
        print(f"     Summary: {data['summary'][:80]}")
        check("summary is non-empty string", len(data["summary"]) > 0)
    else:
        check("summary present", False, "summary is empty/None")

    print(f"     Elapsed: {data.get('elapsed_seconds')}s")
    print(f"     Confidence: {data.get('confidence')}")
except Exception as e:
    check("/api/execute", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  5. History Endpoint
# ══════════════════════════════════════════════════════════════════════

section("5. GET /api/history")

try:
    data = api_get("/api/history")
    check("returns JSON", isinstance(data, dict))
    check("has 'entries'", isinstance(data.get("entries"), list))

    # After executing, we should have at least 1 entry
    entries = data["entries"]
    check(f"has entries after execution: {len(entries)}", len(entries) > 0)
    if entries:
        e = entries[0]
        check("entry has timestamp", "timestamp" in e)
        check("entry has request", "request" in e)
except Exception as e:
    check("/api/history", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  6. Frontend Files Served
# ══════════════════════════════════════════════════════════════════════

section("6. Frontend Static Files")

# index.html at root
try:
    text, status = http_get_text("/")
    check("GET / returns 200", status == 200)
    check("contains <!DOCTYPE html>", "<!DOCTYPE html>" in text)
    check("contains 'PC Automation'", "PC Automation" in text)
    check("links to styles.css", "styles.css" in text)
    check("links to app.js", "app.js" in text)
except Exception as e:
    check("GET /", False, str(e))

# styles.css
try:
    text, status = http_get_text("/static/styles.css")
    check("GET /static/styles.css returns 200", status == 200)
    check("CSS contains :root", ":root" in text)
    check("CSS contains --bg-primary", "--bg-primary" in text)
    check("CSS has glassmorphism", "backdrop-filter" in text)
except Exception as e:
    check("GET /static/styles.css", False, str(e))

# app.js
try:
    text, status = http_get_text("/static/app.js")
    check("GET /static/app.js returns 200", status == 200)
    check("JS contains fetchStatus", "fetchStatus" in text)
    check("JS contains fetchTools", "fetchTools" in text)
    check("JS contains executeCommand or sendChat", "sendChat" in text)
except Exception as e:
    check("GET /static/app.js", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  7. Similarity Endpoint
# ══════════════════════════════════════════════════════════════════════

section("7. GET /api/similarity")

try:
    data = api_get("/api/similarity?query=check+cpu")
    check("returns JSON", isinstance(data, dict))
    check("has 'query'", data.get("query") == "check cpu")
    check("has 'matches'", "matches" in data)
    if data["matches"]:
        m = data["matches"][0]
        check("match has 'tool'", "tool" in m)
        check("match has 'score'", "score" in m)
        print(f"     Top match: {m['tool']} ({m['score']})")
    else:
        print("     No matches (router may not be loaded)")
except Exception as e:
    check("/api/similarity", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  8. Error Handling
# ══════════════════════════════════════════════════════════════════════

section("8. Error Handling")

# Empty command
try:
    data = api_post("/api/execute", {"command": ""})
    check("empty command handled", "results" in data or "error" in data)
except Exception as e:
    # A 422 validation error is also acceptable
    check("empty command returns error", "422" in str(e) or "400" in str(e), str(e))

# Invalid endpoint
try:
    api_get("/api/nonexistent")
    check("404 for missing endpoint", False, "Expected error")
except urllib.error.HTTPError as e:
    check("404 for missing endpoint", e.code == 404, f"Got {e.code}")
except Exception as e:
    check("404 for missing endpoint", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════════════

section("SUMMARY")
total = PASS + FAIL
print(f"\n  Passed: {PASS}/{total}")
print(f"  Failed: {FAIL}/{total}")
if FAIL == 0:
    print("\n  🎉 ALL FRONTEND CONNECTIVITY TESTS PASSED!")
else:
    print(f"\n  ⚠️  {FAIL} test(s) failed")
print()
