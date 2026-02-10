"""
PC Automation Framework - Tool Registry & Executor
"""
from typing import Dict, Callable, Any, List
from dataclasses import dataclass, field
from enum import Enum
from core.logger import logger


class ToolRisk(Enum):
    """Risk levels for tools."""
    SAFE = "safe"           # Read-only, no side effects
    MEDIUM = "medium"       # Reversible changes
    HIGH = "high"           # Destructive or system-altering


@dataclass
class ToolDefinition:
    """Metadata for a registered tool."""
    name: str
    description: str
    risk_level: ToolRisk
    func: Callable
    required_params: List[str]
    semantic_aliases: List[str] = field(default_factory=list)
    sample_queries: List[str] = field(default_factory=list)


class ToolRegistry:
    """
    Central registry for all available tools.
    The Executor can ONLY call tools registered here.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
    
    def register(
        self,
        name: str,
        description: str,
        risk_level: ToolRisk,
        required_params: List[str] = None,
        semantic_aliases: List[str] = None,
        sample_queries: List[str] = None
    ):
        """Decorator to register a tool function."""
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                risk_level=risk_level,
                func=func,
                required_params=required_params or [],
                semantic_aliases=semantic_aliases or [],
                sample_queries=sample_queries or []
            )
            logger.debug(f"Registered tool: {name} (Risk: {risk_level.value})")
            return func
        return decorator
    
    def get(self, name: str) -> ToolDefinition:
        """Get a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools for LLM context."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk": t.risk_level.value,
                "params": t.required_params,
                "aliases": t.semantic_aliases,
                "samples": t.sample_queries
            }
            for t in self._tools.values()
        ]
    
    def get_safe_tools_only(self) -> List[str]:
        """Get names of safe (read-only) tools."""
        return [t.name for t in self._tools.values() if t.risk_level == ToolRisk.SAFE]


# Global registry instance
registry = ToolRegistry()


class Executor:
    """
    Deterministic executor that runs plans step by step.
    NO LLM involvement - just dispatching to registered tools.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry
    
    def execute_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a validated plan.
        Halts on first failure.
        """
        results = []
        steps = plan.get("steps", [])
        
        for step in steps:
            step_id = step.get("step_id", "?")
            tool_name = step.get("tool_name")
            args = step.get("arguments", {})
            on_failure = step.get("on_failure", "abort")
            
            logger.info(f"Executing step {step_id}: {tool_name}")
            
            try:
                # Get tool from registry (security check)
                tool_def = self.registry.get(tool_name)
                
                # Validate required params
                for param in tool_def.required_params:
                    if param not in args:
                        raise ValueError(f"Missing required param: {param}")
                
                # Execute tool
                result = tool_def.func(**args)
                results.append({
                    "step_id": step_id,
                    "status": "success",
                    "result": result
                })
                logger.info(f"Step {step_id} completed successfully")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Step {step_id} failed: {error_msg}")
                results.append({
                    "step_id": step_id,
                    "status": "failed",
                    "error": error_msg
                })
                
                if on_failure == "abort":
                    logger.warning("Aborting execution due to step failure")
                    break
                # else: continue to next step
        
        return results
