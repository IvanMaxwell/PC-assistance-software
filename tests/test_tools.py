"""
PC Automation Framework – Tool Registry & Execution Tests
Run:  python -m pytest tests/test_tools.py -v --tb=short
  or: python tests/test_tools.py
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
#  1. Registry Import & Basic Operations
# ══════════════════════════════════════════════════════════════════════

section("1. Registry Import")

try:
    from tools.registry import registry, ToolMeta, RiskLevel
    check("registry singleton imported", registry is not None)
    check("ToolMeta class exists", ToolMeta is not None)
except Exception as e:
    check("registry import", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  2. Tool Discovery
# ══════════════════════════════════════════════════════════════════════

section("2. Tool Discovery (tools/__init__.py)")

try:
    from tools import discover_tools
    discover_tools()
    names = registry.list_names()
    check("discover_tools() ran", True)
    check(f"tools registered: {len(names)}", len(names) > 0, f"got {len(names)}")
    print(f"     Registered tools: {names}")
except Exception as e:
    check("discover_tools()", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  3. list_tools() Method
# ══════════════════════════════════════════════════════════════════════

section("3. registry.list_tools()")

try:
    tools = registry.list_tools()
    check("list_tools() returns list", isinstance(tools, list))
    check("list_tools() not empty", len(tools) > 0)
    if tools:
        first = tools[0]
        check("tool has 'name' key", "name" in first)
        check("tool has 'risk' key", "risk" in first)
        check("tool has 'category' key", "category" in first)
        check("tool has 'description' key", "description" in first)
except Exception as e:
    check("list_tools()", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  4. to_dict_list() Method
# ══════════════════════════════════════════════════════════════════════

section("4. registry.to_dict_list()")

try:
    dicts = registry.to_dict_list()
    check("to_dict_list() returns list", isinstance(dicts, list))
    check("to_dict_list() has items", len(dicts) > 0)
    if dicts:
        d = dicts[0]
        check("has 'name'", "name" in d)
        check("has 'parameters'", "parameters" in d)
except Exception as e:
    check("to_dict_list()", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  5. Tool Lookup  (registry.get)
# ══════════════════════════════════════════════════════════════════════

section("5. Tool Lookup")

try:
    # We expect at least get_cpu_usage to be registered
    cpu_tool = registry.get("get_cpu_usage")
    check("get('get_cpu_usage') found", cpu_tool is not None)
    if cpu_tool:
        check("tool has callable func", callable(cpu_tool.func))
        check(f"risk_level is string", isinstance(cpu_tool.risk_level, str))
except Exception as e:
    check("tool lookup", False, str(e))

try:
    missing = registry.get("nonexistent_tool_xyz")
    check("get() returns None for missing", missing is None)
except Exception as e:
    check("missing tool lookup", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  6. Tool Execution  (async registry.execute)
# ══════════════════════════════════════════════════════════════════════

section("6. Tool Execution")

async def test_execute():
    # get_cpu_usage - should work without args
    try:
        result = await registry.execute("get_cpu_usage")
        check("execute get_cpu_usage", isinstance(result, dict))
        check("result has status", "status" in result)
        check("status is success", result.get("status") == "success", f"got: {result.get('status')}")
        if result.get("data"):
            check("data has cpu_percent", "cpu_percent" in result["data"])
    except Exception as e:
        check("execute get_cpu_usage", False, str(e))

    # get_memory_usage
    try:
        result = await registry.execute("get_memory_usage")
        check("execute get_memory_usage", result.get("status") == "success")
    except Exception as e:
        check("execute get_memory_usage", False, str(e))

    # get_disk_space
    try:
        result = await registry.execute("get_disk_space", {"drive": "C:\\"})
        check("execute get_disk_space(C:\\)", result.get("status") == "success")
    except Exception as e:
        check("execute get_disk_space", False, str(e))

    # check_internet_connection
    try:
        result = await registry.execute("check_internet_connection")
        check("execute check_internet_connection", result.get("status") == "success")
    except Exception as e:
        check("execute check_internet_connection", False, str(e))

    # get_network_config
    try:
        result = await registry.execute("get_network_config")
        check("execute get_network_config", result.get("status") == "success")
    except Exception as e:
        check("execute get_network_config", False, str(e))

    # Non-existent tool
    try:
        result = await registry.execute("doesnt_exist_123")
        check("execute missing tool returns error", result.get("status") == "error")
    except Exception as e:
        # An exception is also acceptable
        check("execute missing tool raises exception", True)


asyncio.run(test_execute())


# ══════════════════════════════════════════════════════════════════════
#  7. Executor Class
# ══════════════════════════════════════════════════════════════════════

section("7. Executor Class")

try:
    from tools.executor import Executor
    executor = Executor(registry)
    check("Executor instantiated", executor is not None)

    # Simple plan with 1 step
    test_plan = {
        "reasoning": "Test plan",
        "steps": [
            {
                "step_id": 1,
                "tool_name": "get_cpu_usage",
                "arguments": {},
                "on_failure": "abort",
            }
        ]
    }

    results = executor.execute_plan(test_plan, confirm_callback=lambda *a: True)
    check("execute_plan returns list", isinstance(results, list))
    check("execute_plan has results", len(results) > 0)
    if results:
        r = results[0]
        check("result has step_id", "step_id" in r)
        check("result has status", "status" in r)
        check("step succeeded", r.get("status") == "success", f"got: {r}")
except Exception as e:
    check("Executor", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  8. Risk Level Categories
# ══════════════════════════════════════════════════════════════════════

section("8. Risk Levels")

try:
    tools = registry.list_tools()
    risk_counts = {}
    for t in tools:
        r = t["risk"].upper()
        risk_counts[r] = risk_counts.get(r, 0) + 1

    for risk, count in sorted(risk_counts.items()):
        print(f"     {risk}: {count} tools")

    check("has SAFE tools", risk_counts.get("SAFE", 0) > 0)
    check("has MEDIUM or HIGH tools", risk_counts.get("MEDIUM", 0) + risk_counts.get("HIGH", 0) > 0)
except Exception as e:
    check("risk levels", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  9. Category Summary
# ══════════════════════════════════════════════════════════════════════

section("9. Categories")

try:
    tools = registry.list_tools()
    cats = {}
    for t in tools:
        c = t["category"]
        cats[c] = cats.get(c, 0) + 1

    for cat, count in sorted(cats.items()):
        print(f"     {cat}: {count} tools")

    check("multiple categories", len(cats) > 1)
except Exception as e:
    check("categories", False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════════════

section("SUMMARY")
total = PASS + FAIL
print(f"\n  Passed: {PASS}/{total}")
print(f"  Failed: {FAIL}/{total}")
if FAIL == 0:
    print("\n  🎉 ALL TOOL TESTS PASSED!")
else:
    print(f"\n  ⚠️  {FAIL} test(s) failed")
print()
