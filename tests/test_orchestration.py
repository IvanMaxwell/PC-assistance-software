"""
PC Automation Framework – Orchestration Pipeline Tests
Run:  python tests/test_orchestration.py
"""

import sys
import os
import asyncio
import time

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


# ══════════════════════════════════════════════════════════════════════
#  1. Import Core Modules
# ══════════════════════════════════════════════════════════════════════

section("1. Core Imports")

try:
    from core.config import config, State, SafetyMode, CONFIDENCE_THRESHOLD
    check("config imported", config is not None)
    check("State enum imported", State is not None)
    check("SafetyMode enum imported", SafetyMode is not None)
    check(f"CONFIDENCE_THRESHOLD = {CONFIDENCE_THRESHOLD}", CONFIDENCE_THRESHOLD > 0)
except Exception as e:
    check("core.config import", False, str(e))

try:
    from core.logger import logger
    check("logger imported", logger is not None)
except Exception as e:
    check("core.logger import", False, str(e))

try:
    from core.memory import MemoryManager, ShortTermMemory, LongTermMemory
    check("memory classes imported", True)
except Exception as e:
    check("core.memory import", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  2. ExecutionContext
# ══════════════════════════════════════════════════════════════════════

section("2. ExecutionContext")

try:
    from core.orchestrator import ExecutionContext
    ctx = ExecutionContext()
    check("ExecutionContext created", ctx is not None)
    check("user_request default empty", ctx.user_request == "")
    check("results default empty list", ctx.results == [])
    check("confidence_score default 0", ctx.confidence_score == 0.0)
    check("cm_response default None", ctx.cm_response is None)
    check("cs_assessment default None", ctx.cs_assessment is None)

    ctx2 = ExecutionContext(user_request="test query")
    check("user_request set", ctx2.user_request == "test query")
except Exception as e:
    check("ExecutionContext", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  3. Orchestrator Init (no LLM loaded yet)
# ══════════════════════════════════════════════════════════════════════

section("3. Orchestrator Init")

try:
    from core.orchestrator import Orchestrator
    from tools import discover_tools
    discover_tools()

    orch = Orchestrator(display=None)
    check("Orchestrator created", orch is not None)
    check("initial state is IDLE", orch.state == State.IDLE)
    check("context exists", orch.context is not None)
    check("handlers registered", len(orch._handlers) > 0)
    check(f"handlers count = {len(orch._handlers)}", len(orch._handlers) >= 8)
except Exception as e:
    check("Orchestrator init", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  4. State Transitions
# ══════════════════════════════════════════════════════════════════════

section("4. State Transitions")

try:
    orch = Orchestrator(display=None)
    check("starts IDLE", orch.state == State.IDLE)

    orch.transition(State.NEGOTIATING)
    check("transition to NEGOTIATING", orch.state == State.NEGOTIATING)

    orch.transition(State.DIAGNOSING)
    check("transition to DIAGNOSING", orch.state == State.DIAGNOSING)

    orch.transition(State.PLANNING)
    check("transition to PLANNING", orch.state == State.PLANNING)

    orch.transition(State.IDLE)
    check("transition back to IDLE", orch.state == State.IDLE)
except Exception as e:
    check("transitions", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  5. WebDisplay Adapter (event capture)
# ══════════════════════════════════════════════════════════════════════

section("5. WebDisplay Adapter")

try:
    events = []

    class TestDisplay:
        def show_state_transition(self, from_s, to_s):
            events.append({"type": "state", "from": from_s, "to": to_s})
        def show_cm_response(self, resp):
            events.append({"type": "cm_response", **resp})
        def show_plan(self, plan):
            events.append({"type": "plan", "steps": len(plan.get("steps", []))})
        def show_confidence(self, score):
            events.append({"type": "confidence", "score": score})
        def show_risk_assessment(self, assessment):
            events.append({"type": "risk", **assessment})
        def show_step_result(self, step_id, tool, status, result=None, error=None):
            events.append({"type": "step", "tool": tool, "status": status})
        def show_drift_alert(self, drift):
            events.append({"type": "drift"})
        def show_final_summary(self, summary):
            events.append({"type": "summary", "text": summary})
        def ask_permission(self, step_id, tool_name, risk, args):
            return True
        def show_router_result(self, query, tool, score, hit):
            events.append({"type": "router", "tool": tool, "score": score, "hit": hit})

    td = TestDisplay()
    orch = Orchestrator(display=td)
    orch.transition(State.NEGOTIATING)
    check("display captured state transition", len(events) > 0)
    check("event is state type", events[0]["type"] == "state")
    check("from is IDLE", events[0]["from"] == "idle")
    check("to is NEGOTIATING", events[0]["to"] == "negotiating")
except Exception as e:
    check("WebDisplay adapter", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  6. Memory Manager
# ══════════════════════════════════════════════════════════════════════

section("6. Memory Manager")

try:
    mm = MemoryManager()
    check("MemoryManager created", mm is not None)
    check("short_term exists", mm.short_term is not None)
    check("long_term exists", mm.long_term is not None)

    mm.store_execution_result({"request": "test", "results": []})
    recent = mm.short_term.get_recent(5)
    check("stored entry in short-term", len(recent) >= 1)

    ctx_for_planner = mm.get_context_for_planner()
    check("context_for_planner has recent", "recent_executions" in ctx_for_planner)
    check("context_for_planner has safety_rules", "safety_rules" in ctx_for_planner)
    check("context_for_planner has patterns", "known_patterns" in ctx_for_planner)
except Exception as e:
    check("MemoryManager", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  7. CM Agent Import & Status
# ══════════════════════════════════════════════════════════════════════

section("7. CM Agent")

try:
    from llm.cm_agent import CMAgent
    cm = CMAgent()
    check("CMAgent created", cm is not None)

    status = cm.get_status()
    check("get_status() returns dict", isinstance(status, dict))
    print(f"     CM status: {status}")
except Exception as e:
    check("CMAgent", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  8. CS Agent Import & Status
# ══════════════════════════════════════════════════════════════════════

section("8. CS Agent")

try:
    from llm.cs_agent import CSAgent
    cs = CSAgent()
    check("CSAgent created", cs is not None)

    status = cs.get_status()
    check("get_status() returns dict", isinstance(status, dict))
    print(f"     CS status: {status}")
except Exception as e:
    check("CSAgent", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  9. CM Agent: process_message
# ══════════════════════════════════════════════════════════════════════

section("9. CM Agent: process_message()")

try:
    cm = CMAgent()
    result = asyncio.run(cm.process_message("Check my CPU usage"))
    check("process_message returns dict", isinstance(result, dict))
    check("has 'reply'", "reply" in result)
    check("has 'explanation'", "explanation" in result)
    print(f"     Reply: {result.get('reply', '')[:80]}")
except Exception as e:
    check("process_message", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 10. CS Agent: evaluate_plan (rule-based)
# ══════════════════════════════════════════════════════════════════════

section("10. CS Agent: evaluate_plan()")

try:
    cs = CSAgent()
    safe_plan = {
        "steps": [
            {"step_id": 1, "tool_name": "get_cpu_usage", "arguments": {}}
        ]
    }
    result = asyncio.run(cs.evaluate_plan(safe_plan))
    check("evaluate_plan returns dict", isinstance(result, dict))
    check("has risk_level", "risk_level" in result)
    check("has recommendation", "recommendation" in result)
    print(f"     Risk: {result.get('risk_level')}, Rec: {result.get('recommendation')}")
except Exception as e:
    check("evaluate_plan", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 11. Orchestrator get_status()
# ══════════════════════════════════════════════════════════════════════

section("11. Orchestrator get_status()")

try:
    orch = Orchestrator(display=None)
    status = orch.get_status()
    check("get_status() returns dict", isinstance(status, dict))
    check("has orchestrator key", "orchestrator" in status)
    check("has cm_agent key", "cm_agent" in status)
    check("has cs_agent key", "cs_agent" in status)
    check("has planner key", "planner" in status)
    print(f"     Status keys: {list(status.keys())}")
except Exception as e:
    check("get_status()", False, str(e))


# ══════════════════════════════════════════════════════════════════════
# 12. Config Values
# ══════════════════════════════════════════════════════════════════════

section("12. Config Values")

try:
    check(f"safety_mode = {config.safety_mode.value}", config.safety_mode is not None)
    check(f"local_model_path exists", config.local_model_path is not None)
    print(f"     Model path: {config.local_model_path}")

    # Verify all State enum values
    expected_states = ["IDLE", "NEGOTIATING", "DIAGNOSING", "PLANNING",
                       "SCORING", "VALIDATING", "EXECUTING", "REPORTING",
                       "LEARNING", "ERROR_RECOVERY"]
    for s in expected_states:
        try:
            state = State(s.lower())
            check(f"State.{s} exists", True)
        except ValueError:
            check(f"State.{s} exists", False, f"'{s.lower()}' not in enum")
except Exception as e:
    check("config values", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════════════

section("SUMMARY")
total = PASS + FAIL
print(f"\n  Passed: {PASS}/{total}")
print(f"  Failed: {FAIL}/{total}")
if FAIL == 0:
    print("\n  🎉 ALL ORCHESTRATION TESTS PASSED!")
else:
    print(f"\n  ⚠️  {FAIL} test(s) failed")
print()
