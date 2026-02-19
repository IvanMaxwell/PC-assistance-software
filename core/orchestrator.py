"""
PC Automation Framework - Orchestrator (FSM)
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
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
            from tools.registry import Executor, registry
            self._executor = Executor(registry)
        
        if self._memory is None:
            from core.memory import MemoryManager
            self._memory = MemoryManager()
    
    def transition(self, new_state: State):
        """Transition to a new state."""
        if self._display:
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
                    self.context.error = str(e)
                    self.transition(State.ERROR_RECOVERY)
            else:
                logger.error(f"No handler for state: {self.state.value}")
                break
        
        # Handle final error state if needed
        if self.state == State.ERROR_RECOVERY:
            self._handle_error()
        
        return self.context.results
    
    def cleanup(self):
        """Cleanup resources (unload LLM)."""
        if self._planner:
            self._planner.unload()
    
    # --- State Handlers ---
    
    def _handle_idle(self):
        """Waiting for input."""
        pass
    
    def _handle_negotiating(self):
        """Clarify user intent, extract goal and constraints."""
        logger.info("Negotiating: Parsing user request...")
        
        # Check Semantic Router shortcut
        try:
            from core.router import get_router
            router = get_router()
            if router:
                fast_plan = router.find_tool(self.context.user_request)
                if fast_plan:
                    self.context.current_plan = fast_plan
                    # Skip Diagnosing/Planning/Scoring -> Go straight to Execution
                    if self._display:
                        self._display.show_router_result(
                            self.context.user_request,
                            fast_plan['steps'][0]['tool_name'],
                            fast_plan.get('confidence_prediction', 0),
                            hit=True
                        )
                    logger.info("🚀 Semantic Router Shortcut Activated!")
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
        
        # Run safe diagnostic tools
        diagnostics = {}
        try:
            sys_info = registry.get("sys.get_info")
            diagnostics["system"] = sys_info.func()
        except Exception as e:
            logger.warning(f"sys.get_info failed: {e}")
        
        try:
            net_info = registry.get("net.get_config")
            diagnostics["network"] = net_info.func()
        except Exception as e:
            logger.warning(f"net.get_config failed: {e}")
        
        try:
            net_conn = registry.get("net.check_connection")
            diagnostics["connectivity"] = net_conn.func()
        except Exception as e:
            logger.warning(f"net.check_connection failed: {e}")
        
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
            available_tools=registry.list_tools(),
            memory_context=self._memory.get_context_for_planner()
        )
        
        if plan is None:
            self.context.error = "Failed to generate plan"
            self.transition(State.ERROR_RECOVERY)
            return
        
        self.context.current_plan = plan
        if self._display:
            self._display.show_plan(plan)
        logger.info(f"Plan generated: {plan.get('reasoning', 'No reasoning')[:100]}...")
        self.transition(State.SCORING)
    
    def _handle_scoring(self):
        """Calculate confidence score deterministically."""
        logger.info("Scoring: Evaluating plan confidence...")
        
        plan = self.context.current_plan
        score = 1.0
        
        # Check if all tools exist
        from tools.registry import registry
        for step in plan.get("steps", []):
            tool_name = step.get("tool_name", "")
            try:
                registry.get(tool_name)
            except KeyError:
                logger.warning(f"Unknown tool in plan: {tool_name}")
                score -= 0.3
        
        # Use LLM's self-predicted confidence
        llm_confidence = plan.get("confidence_prediction", 0.5)
        score = (score + llm_confidence) / 2
        
        self.context.confidence_score = max(0.0, min(1.0, score))
        if self._display:
            self._display.show_confidence(self.context.confidence_score)
        logger.info(f"Confidence score: {self.context.confidence_score:.2f}")
        
        if self.context.confidence_score >= CONFIDENCE_THRESHOLD:
            self.transition(State.EXECUTING)
        else:
            self.transition(State.VALIDATING)
    
    def _handle_validating(self):
        """Call Validator LLM for low-confidence plans."""
        logger.info("Validating: Low confidence, requesting validation...")
        # TODO: Implement validator LLM call
        # For now, proceed with warning
        logger.warning("Validator not implemented, proceeding with caution")
        self.transition(State.EXECUTING)
    
    def _handle_executing(self):
        """Execute plan steps deterministically via Tool Registry."""
        logger.info("Executing: Running plan steps...")
        
        def check_permission(step_id, tool_name, risk, args) -> bool:
            """Callback for permission check."""
            mode = config.safety_mode
            
            # Autonomous: never ask
            if mode == SafetyMode.AUTONOMOUS:
                return True
                
            # Semi-Autonomous: ask only for MEDIUM/HIGH
            if mode == SafetyMode.SEMI_AUTONOMOUS and risk == "safe":
                return True
            
            # Safe Mode (Default): Ask for everything
            # Or if it's Semi/High risk
            if self._display:
                return self._display.ask_permission(step_id, tool_name, risk, args)
            
            # If no display but requires permission, assume denied for safety
            logger.warning(f"Permission required for {tool_name} but no display attached.")
            return False

        results = self._executor.execute_plan(
            self.context.current_plan,
            confirm_callback=check_permission
        )
        self.context.results = results
        
        # Display step results
        if self._display:
            for r in results:
                self._display.show_step_result(
                    step_id=r.get('step_id', 0),
                    tool=r.get('tool', 'unknown'),
                    status=r.get('status', 'unknown'),
                    result=r.get('result'),
                    error=r.get('error')
                )
        
        # Check for failures
        failures = [r for r in results if r.get("status") == "failed"]
        if failures:
            logger.warning(f"Execution had {len(failures)} failures")
        
        self.transition(State.REPORTING)
    
    def _handle_reporting(self):
        """Generate and display a summary of the execution."""
        logger.info("Reporting: Generating summary...")
        
        summary = self._planner.generate_summary(
            goal=self.context.user_request,
            plan=self.context.current_plan,
            results=self.context.results
        )
        
        self.context.summary = summary
        
        if self._display:
            self._display.show_final_summary(summary)
        
        self.transition(State.LEARNING)
    
    def _handle_learning(self):
        """Store results in memory."""
        logger.info("Learning: Storing results in memory...")
        self._memory.store_execution_result({
            "request": self.context.user_request,
            "plan": self.context.current_plan,
            "results": self.context.results,
            "confidence": self.context.confidence_score
        })
        self.transition(State.IDLE)
    
    def _handle_error(self):
        """Handle errors gracefully."""
        logger.error(f"Error Recovery: {self.context.error}")
        self.context.results.append({
            "status": "error",
            "error": self.context.error
        })
        self.transition(State.IDLE)
