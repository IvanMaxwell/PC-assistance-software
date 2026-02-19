"""
PC Automation Framework – Plan Executor
Deterministically executes the steps in a plan using the ToolRegistry.
"""

import asyncio
from typing import Dict, Any, Callable, Optional, List
from core.logger import logger


class Executor:
    """
    Executes a JSON plan step-by-step using the tool registry.
    Checks permissions before running risky tools.
    """

    def __init__(self, registry):
        """
        Args:
            registry: The ToolRegistry singleton.
        """
        self._registry = registry

    def execute_plan(
        self,
        plan: Dict[str, Any],
        confirm_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        Execute all steps in a plan sequentially.

        Args:
            plan:             Parsed JSON plan with a "steps" list.
            confirm_callback: fn(step_id, tool_name, risk, args) -> bool.
                              If it returns False the step is skipped.

        Returns:
            List of result dicts, one per step.
        """
        steps = plan.get("steps", [])
        results: List[Dict] = []

        for step in steps:
            step_id = step.get("step_id", len(results) + 1)
            tool_name = step.get("tool_name") or step.get("tool", "")
            arguments = step.get("arguments") or step.get("params", {})
            on_failure = step.get("on_failure", "abort")

            # ── Look up the tool ────────────────────────────────────
            tool_meta = self._registry.get(tool_name)
            if tool_meta is None:
                msg = f"Tool '{tool_name}' not found in registry"
                logger.error(msg)
                results.append({
                    "step_id": step_id,
                    "tool": tool_name,
                    "status": "failed",
                    "error": msg,
                })
                if on_failure == "abort":
                    break
                continue

            risk = tool_meta.risk_level
            if hasattr(risk, "value"):
                risk = risk.value

            # ── Permission check ────────────────────────────────────
            if confirm_callback:
                allowed = confirm_callback(step_id, tool_name, risk, arguments)
                if not allowed:
                    logger.info(f"Step {step_id} ({tool_name}) denied by user")
                    results.append({
                        "step_id": step_id,
                        "tool": tool_name,
                        "status": "skipped",
                        "error": "Permission denied by user",
                    })
                    if on_failure == "abort":
                        break
                    continue

            # ── Execute ─────────────────────────────────────────────
            try:
                result = self._run(tool_name, arguments)
                status = result.get("status", "success") if isinstance(result, dict) else "success"
                results.append({
                    "step_id": step_id,
                    "tool": tool_name,
                    "status": status,
                    "result": result,
                })
                logger.info(f"Step {step_id} ({tool_name}): {status}")
            except Exception as e:
                logger.error(f"Step {step_id} ({tool_name}) failed: {e}")
                results.append({
                    "step_id": step_id,
                    "tool": tool_name,
                    "status": "failed",
                    "error": str(e),
                })
                if on_failure == "abort":
                    break

        return results

    # ── Internal helpers ─────────────────────────────────────────────

    def _run(self, tool_name: str, arguments: Dict) -> Any:
        """Run a single tool, handling both sync and async callables."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = self._registry.execute(tool_name, arguments)

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)
