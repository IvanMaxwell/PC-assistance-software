"""
PC Automation Framework - Orchestrator (FSM)
Integrates CM Agent, CS Agent, Planner, Executor, and Memory.
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
import asyncio
from core.config import State, CONFIDENCE_THRESHOLD, config, SafetyMode
from core.logger import logger


@dataclass
class ExecutionContext:
    """Holds the current execution state."""
    user_request: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    current_plan: Optional[Dict] = None
    confidence_score: float = 0.0
    current_step_index: int = 0
    results: list = field(default_factory=list)
    error: Optional[str] = None
    summary: str = ""
    cm_response: Optional[Dict] = None
    cs_assessment: Optional[Dict] = None


class Orchestrator:
    """
    Finite State Machine that controls the entire execution flow.
    LLMs are called as external services; execution is deterministic.
    """

    def __init__(self, model_path: str = None, display=None):
        self.state = State.IDLE
        self.context = ExecutionContext()
        self._handlers: Dict[State, Callable] = {}
        self._model_path = model_path or config.local_model_path
        self._planner = None
        self._executor = None
        self._memory = None
        self._cm_agent = None
        self._cs_agent = None
        self._display = display
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register state handlers."""
        self._handlers = {
            State.IDLE: self._handle_idle,
            State.NEGOTIATING: self._handle_negotiating,
            State.DIAGNOSING: self._handle_diagnosing,
            State.PLANNING: self._handle_planning,
            State.SCORING: self._handle_scoring,
            State.VALIDATING: self._handle_validating,
            State.EXECUTING: self._handle_executing,
            State.REPORTING: self._handle_reporting,
            State.LEARNING: self._handle_learning,
            State.ERROR_RECOVERY: self._handle_error,
        }

    def _lazy_init(self):
        """Lazy-initialize components."""
        if self._planner is None:
            from llm.planner.planner import PlannerLLM
            self._planner = PlannerLLM(self._model_path)

        if self._executor is None:
            from tools.registry import registry
            from tools.executor import Executor
            self._executor = Executor(registry)

        if self._memory is None:
            from core.memory import MemoryManager
            self._memory = MemoryManager()

        if self._cm_agent is None:
            from llm.cm_agent import CMAgent
            self._cm_agent = CMAgent()

        if self._cs_agent is None:
            from llm.cs_agent import CSAgent
            self._cs_agent = CSAgent()

    def transition(self, new_state: State):
        """Transition to a new state."""
        if self._display and hasattr(self._display, 'show_state_transition'):
            self._display.show_state_transition(self.state.value, new_state.value)
        logger.info(f"Transition: {self.state.value} -> {new_state.value}")
        self.state = new_state

    def run(self, user_request: str):
        """Main entry point - process a user request."""
        self._lazy_init()
        self.context = ExecutionContext(user_request=user_request)
        self.transition(State.NEGOTIATING)

        # Run state machine until IDLE or ERROR
        while self.state not in (State.IDLE, State.ERROR_RECOVERY):
            handler = self._handlers.get(self.state)
            if handler:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Error in state {self.state.value}: {e}")
                    import traceback
                    traceback.print_exc()
                    self.context.error = str(e)
                    self.transition(State.ERROR_RECOVERY)
            else:
                logger.error(f"No handler for state: {self.state.value}")
                break

        # Handle final error state if needed
        if self.state == State.ERROR_RECOVERY:
            self._handle_error()

        return self.context.results

    def get_status(self) -> dict:
        """Return status of all sub-components."""
        self._lazy_init()
        return {
            "orchestrator": {"state": self.state.value},
            "cm_agent": self._cm_agent.get_status() if self._cm_agent else {"online": False},
            "cs_agent": self._cs_agent.get_status() if self._cs_agent else {"online": False},
            "planner": {"online": self._planner is not None},
        }

    def cleanup(self):
        """Cleanup resources (unload LLM)."""
        if self._planner:
            self._planner.unload()

    # --- Helpers for running async code in sync handlers ---

    @staticmethod
    def _run_async(coro):
        """Run an async coroutine from a synchronous context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    # --- State Handlers ---

    def _handle_idle(self):
        """Waiting for input."""
        pass

    def _handle_negotiating(self):
        """Clarify user intent via CM Agent, check semantic router."""
        logger.info("Negotiating: Parsing user request...")

        # CM Agent: Process message for acknowledgement & explanation
        if self._cm_agent:
            try:
                response = self._run_async(
                    self._cm_agent.process_message(self.context.user_request)
                )
                self.context.cm_response = response
                logger.info(f"CM Agent reply: {response.get('reply', '')}")
                if self._display and hasattr(self._display, 'show_cm_response'):
                    self._display.show_cm_response(response)
            except Exception as e:
                logger.warning(f"CM Agent processing failed: {e}")

        # Check Semantic Router shortcut
        try:
            from core.router import get_router
            router = get_router()
            if router:
                fast_plan = router.find_tool(self.context.user_request)
                if fast_plan:
                    self.context.current_plan = fast_plan
                    if self._display and hasattr(self._display, 'show_router_result'):
                        self._display.show_router_result(
                            self.context.user_request,
                            fast_plan['steps'][0]['tool_name'],
                            fast_plan.get('confidence_prediction', 0),
                            hit=True,
                        )
                    logger.info("Semantic Router Shortcut Activated!")
                    self.transition(State.EXECUTING)
                    return
        except Exception as e:
            logger.warning(f"Router check failed: {e}")

        # Standard flow
        self.transition(State.DIAGNOSING)

    def _handle_diagnosing(self):
        """Run diagnostic tools to gather system context."""
        logger.info("Diagnosing: Gathering system state...")
        from tools.registry import registry

        diagnostics = {}

        for tool_name, label in [
            ("get_cpu_usage", "cpu"),
            ("get_memory_usage", "memory"),
            ("get_network_config", "network"),
            ("check_internet_connection", "connectivity"),
        ]:
            try:
                result = self._run_async(registry.execute(tool_name))
                if isinstance(result, dict) and result.get("status") != "error":
                    diagnostics[label] = result
            except Exception as e:
                logger.warning(f"{tool_name} failed: {e}")

        self.context.diagnostics = diagnostics
        logger.info(f"Diagnostics gathered: {list(diagnostics.keys())}")
        self.transition(State.PLANNING)

    def _handle_planning(self):
        """Call Planner LLM to generate a JSON plan."""
        logger.info("Planning: Requesting plan from LLM...")

        from tools.registry import registry

        plan = self._planner.generate_plan(
            goal=self.context.user_request,
            diagnostics=self.context.diagnostics,
            available_tools=registry.to_dict_list(),
            memory_context=self._memory.get_context_for_planner(),
        )

        if plan is None:
            self.context.error = "Failed to generate plan"
            self.transition(State.ERROR_RECOVERY)
            return

        self.context.current_plan = plan
        if self._display and hasattr(self._display, 'show_plan'):
            self._display.show_plan(plan)
        logger.info(f"Plan generated with {len(plan.get('steps', []))} steps")
        self.transition(State.SCORING)

    def _handle_scoring(self):
        """Calculate confidence score deterministically."""
        logger.info("Scoring: Evaluating plan confidence...")

        plan = self.context.current_plan
        score = 1.0

        from tools.registry import registry
        for step in plan.get("steps", []):
            tool_name = step.get("tool_name", "") or step.get("tool", "")
            if not registry.get(tool_name):
                logger.warning(f"Unknown tool in plan: {tool_name}")
                score -= 0.3

        llm_confidence = plan.get("confidence_prediction", 0.5)
        score = (score + llm_confidence) / 2

        self.context.confidence_score = max(0.0, min(1.0, score))
        if self._display and hasattr(self._display, 'show_confidence'):
            self._display.show_confidence(self.context.confidence_score)
        logger.info(f"Confidence score: {self.context.confidence_score:.2f}")

        if self.context.confidence_score >= CONFIDENCE_THRESHOLD:
            self.transition(State.EXECUTING)
        else:
            self.transition(State.VALIDATING)

    def _handle_validating(self):
        """CS Agent evaluates plan risk when confidence < 0.7."""
        logger.info("Validating: Low confidence, requesting CS Agent review...")

        # CS Agent: Only active when confidence < 0.7 (per user requirement)
        if self.context.confidence_score < 0.7 and self._cs_agent:
            logger.info("CS Agent triggered (confidence < 0.7)")
            try:
                assessment = self._run_async(
                    self._cs_agent.evaluate_plan(self.context.current_plan)
                )
                self.context.cs_assessment = assessment
                logger.info(f"CS Agent: risk={assessment.get('risk_level')}, rec={assessment.get('recommendation')}")

                if self._display and hasattr(self._display, 'show_risk_assessment'):
                    self._display.show_risk_assessment(assessment)

                recommendation = assessment.get("recommendation", "APPROVE")
                if recommendation == "REJECT":
                    self.context.error = (
                        f"Plan rejected by CS Agent. "
                        f"Concerns: {assessment.get('concerns', [])}"
                    )
                    self.transition(State.ERROR_RECOVERY)
                    return

            except Exception as e:
                logger.error(f"CS Agent evaluation failed: {e}")
        else:
            logger.info("CS Agent not triggered (confidence >= 0.7 or agent unavailable)")

        logger.warning("Proceeding with caution after validation")
        self.transition(State.EXECUTING)

    def _handle_executing(self):
        """Execute plan steps deterministically via Executor."""
        logger.info("Executing: Running plan steps...")

        def check_permission(step_id, tool_name, risk, args) -> bool:
            mode = config.safety_mode
            if mode == SafetyMode.AUTONOMOUS:
                return True
            if mode == SafetyMode.SEMI_AUTONOMOUS and risk.upper() == "SAFE":
                return True
            if self._display and hasattr(self._display, 'ask_permission'):
                return self._display.ask_permission(step_id, tool_name, risk, args)
            logger.warning(f"Permission required for {tool_name} but no display attached.")
            return False

        results = self._executor.execute_plan(
            self.context.current_plan,
            confirm_callback=check_permission,
        )
        self.context.results = results

        # CM Agent: Monitor each step result for drift
        if self._cm_agent:
            for r in results:
                try:
                    drift = self._run_async(self._cm_agent.monitor_step(r))
                    if drift.get("drift_detected"):
                        logger.warning(f"CM drift alert: {drift.get('message')}")
                        if self._display and hasattr(self._display, 'show_drift_alert'):
                            self._display.show_drift_alert(drift)
                except Exception as e:
                    logger.warning(f"CM Agent monitoring error: {e}")

        # Display step results
        if self._display and hasattr(self._display, 'show_step_result'):
            for r in results:
                self._display.show_step_result(
                    step_id=r.get('step_id', 0),
                    tool=r.get('tool', 'unknown'),
                    status=r.get('status', 'unknown'),
                    result=r.get('result'),
                    error=r.get('error'),
                )

        failures = [r for r in results if r.get("status") == "failed"]
        if failures:
            logger.warning(f"Execution had {len(failures)} failure(s)")

        self.transition(State.REPORTING)

    def _handle_reporting(self):
        """Generate a natural-language summary via CM Agent."""
        logger.info("Reporting: Generating summary...")

        # Prefer CM Agent for summary (uses Gemini)
        if self._cm_agent:
            try:
                summary = self._run_async(
                    self._cm_agent.summarize_execution(
                        self.context.results,
                        user_input=self.context.user_request,
                    )
                )
            except Exception as e:
                logger.warning(f"CM Agent summary failed: {e}")
                summary = self._fallback_summary()
        else:
            summary = self._fallback_summary()

        self.context.summary = summary

        if self._display and hasattr(self._display, 'show_final_summary'):
            self._display.show_final_summary(summary)

        self.transition(State.LEARNING)

    def _fallback_summary(self) -> str:
        """Simple summary when CM Agent / Planner are unavailable."""
        successes = sum(1 for r in self.context.results if r.get("status") == "success")
        total = len(self.context.results)
        if successes == total:
            return f"All {total} step(s) completed successfully."
        return f"{successes}/{total} steps succeeded."

    def _handle_learning(self):
        """Store results in memory for future context."""
        logger.info("Learning: Storing results in memory...")
        self._memory.store_execution_result({
            "request": self.context.user_request,
            "plan": self.context.current_plan,
            "results": self.context.results,
            "confidence": self.context.confidence_score,
        })
        self.transition(State.IDLE)

    def _handle_error(self):
        """Handle errors gracefully."""
        logger.error(f"Error Recovery: {self.context.error}")
        self.context.results.append({
            "status": "error",
            "error": self.context.error,
        })
        self.transition(State.IDLE)
