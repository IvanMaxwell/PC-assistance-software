"""
Tool Registry - Central registration system for all automation tools.
Uses decorator pattern: @registry.register(risk_level="SAFE", category="system")
"""

import inspect
from typing import Optional, Callable, Dict, List, Any
from functools import wraps
from enum import Enum


class RiskLevel(Enum):
    SAFE = "SAFE"       # Read-only, no side effects
    MEDIUM = "MEDIUM"   # Reversible changes
    HIGH = "HIGH"       # Potentially dangerous / irreversible


class ToolMeta:
    """Metadata for a registered tool."""
    __slots__ = ("name", "func", "risk_level", "category", "description", "parameters")

    def __init__(self, name: str, func: Callable, risk_level: str,
                 category: str, description: str, parameters: List[Dict]):
        self.name = name
        self.func = func
        self.risk_level = risk_level
        self.category = category
        self.description = description
        self.parameters = parameters


class ToolRegistry:
    """
    Singleton registry for all automation tools.

    Usage:
        @registry.register(risk_level="SAFE", category="system")
        def get_cpu_usage(process_name: Optional[str] = None) -> dict:
            ...
    """

    def __init__(self):
        self._tools: Dict[str, ToolMeta] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, risk_level: str = "SAFE", category: str = "general"):
        """Decorator to register a tool function."""

        def decorator(func: Callable) -> Callable:
            tool_name = func.__name__
            description = (func.__doc__ or "").strip().split("\n")[0]

            # Extract parameter info from type hints
            sig = inspect.signature(func)
            parameters = []
            for pname, param in sig.parameters.items():
                ptype = "string"
                if param.annotation != inspect.Parameter.empty:
                    ptype = getattr(param.annotation, "__name__", str(param.annotation))
                parameters.append({
                    "name": pname,
                    "type": ptype,
                    "required": param.default is inspect.Parameter.empty,
                    "default": None if param.default is inspect.Parameter.empty else param.default,
                })

            meta = ToolMeta(
                name=tool_name,
                func=func,
                risk_level=risk_level,
                category=category,
                description=description,
                parameters=parameters,
            )
            self._tools[tool_name] = meta

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            wrapper._tool_meta = meta
            return wrapper

        return decorator

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[ToolMeta]:
        return self._tools.get(name)

    def get_all(self) -> Dict[str, ToolMeta]:
        return dict(self._tools)

    def get_by_category(self, category: str) -> List[ToolMeta]:
        return [t for t in self._tools.values() if t.category == category]

    def get_by_risk(self, risk_level: str) -> List[ToolMeta]:
        return [t for t in self._tools.values() if t.risk_level == risk_level]

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def list_tools(self) -> List[Dict]:
        """Return tools as simple dicts (used by display, router, main)."""
        out = []
        for t in self._tools.values():
            risk = t.risk_level
            if hasattr(risk, "value"):
                risk = risk.value
            out.append({
                "name": t.name,
                "description": t.description,
                "risk": risk.lower() if isinstance(risk, str) else str(risk),
                "category": t.category,
                "params": [p for p in t.parameters if p.get("required")],
            })
        return out

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, name: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """Execute a tool by name with the given parameters (handles both sync and async)."""
        meta = self._tools.get(name)
        if not meta:
            return {"status": "error", "message": f"Tool '{name}' not found"}

        try:
            import asyncio
            if asyncio.iscoroutinefunction(meta.func):
                result = await meta.func(**(params or {}))
            else:
                # Run sync functions in a thread to avoid blocking the event loop
                result = await asyncio.to_thread(meta.func, **(params or {}))
            return result
        except TypeError as e:
            return {"status": "error", "message": f"Invalid parameters: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Execution failed: {e}"}

    # ------------------------------------------------------------------
    # Serialisation (for API / Planner)
    # ------------------------------------------------------------------

    def to_dict_list(self) -> List[Dict]:
        """Return all tools as serialisable dicts (for API responses)."""
        return [
            {
                "name": t.name,
                "risk_level": t.risk_level,
                "category": t.category,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self._tools.values()
        ]


# Module-level singleton
registry = ToolRegistry()
