# Implementation Plan: Safety Net & Stress Testing

## 1. Safety Net (Permissions System)
Before stress testing, we must implement a robust permission system to prevent unintended destructive actions.

### Implementation Details:
1.  **Modify `core/config.py`:**
    -   Add a `SafetyMode` enum: `SAFE` (ask for all), `SEMI_AUTONOMOUS` (ask for high risk), `AUTONOMOUS` (no asking).
    -   Add `safety_mode` to `APIConfig`.

2.  **Modify `core/orchestrator.py`:**
    -   In `_handle_executing`, prior to executing *each* step:
        -   Check the tool's risk level from `ToolRegistry`.
        -   Check `config.safety_mode`.
        -   If permission is required (`confirms_action`), prompt the user.
    -   If denied, skip the step or abort the plan (configurable).

3.  **Modify `core/display.py`:**
    -   Add `ask_permission(step_id, tool_name, risk_level, arguments) -> bool` method.
    -   Use `rich.prompt` to get Y/n input.

## 2. Stress Testing Strategy
We will create a dedicated `tests/stress_test.py` script.

### Strategy:
1.  **High Volume of Requests:**
    -   Loop 50-100 simple read-only requests (e.g., "list files", "check ip") to test router/LLM stability and memory usage.
2.  **Rapid State Transitions:**
    -   Force the FSM through cycles quickly to check for race conditions or state leaks.
3.  **Error Injection:**
    -   Simulate tool failures (mock tools that raise exceptions) to verify `ERROR_RECOVERY` handling.
4.  **Resource Monitoring:**
    -   Use `psutil` within the test script to log memory/CPU usage of the framework itself during the test.

### Proposed Test Script Structure:
```python
def run_stress_test(iterations=50):
    for i in range(iterations):
        # 1. Randomly pick a safe query
        # 2. Run orchestrator
        # 3. Measure time & memory
        # 4. Assert success/failure
```

## Next Steps
1.  Implement Safety Net (Config, Display, Orchestrator).
2.  Create `tests/stress_test.py`.
3.  Run Stress Test and monitor.

