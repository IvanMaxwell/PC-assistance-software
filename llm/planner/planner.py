"""
PC Automation Framework - Planner LLM Interface
"""
import json
import os
from typing import Dict, Any, Optional
from core.config import config
from core.logger import logger
from llm.prompts import build_planner_prompt, PLAN_SCHEMA
from llm.local_llm import LocalLLM, format_chat_prompt


class PlannerLLM:
    """
    Interface to the Planner LLM (local Deepseek R1).
    Generates structured JSON plans from user goals.
    """
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or config.local_model_path
        self._llm: Optional[LocalLLM] = None
    
    def _ensure_loaded(self):
        """Ensure LLM is loaded."""
        if self._llm is None:
            self._llm = LocalLLM(
                model_path=self.model_path,
                n_ctx=4096,
                n_gpu_layers=-1  # Use all GPU layers
            )
            self._llm.load()
    
    def unload(self):
        """Unload the LLM to free memory."""
        if self._llm:
            self._llm.unload()
            self._llm = None
    
    def generate_plan(
        self,
        goal: str,
        diagnostics: Dict[str, Any],
        available_tools: list,
        memory_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a plan for the given goal.
        
        Returns:
            Parsed JSON plan or None if generation fails.
        """
        self._ensure_loaded()
        
        # Build the user prompt content
        user_content = build_planner_prompt(
            goal, diagnostics, available_tools, memory_context
        )
        
        # Build system prompt
        system_prompt = """You are a PC Automation Planner. Generate a JSON plan to solve computer problems.

RULES:
1. Only use tools from the provided list
2. Include step dependencies
3. For risky operations, add backup steps FIRST
4. Output ONLY valid JSON, no explanation

OUTPUT FORMAT:
{
  "reasoning": "Brief explanation of approach",
  "confidence_prediction": 0.0-1.0,
  "steps": [
    {
      "step_id": 1,
      "tool_name": "exact_tool_name",
      "arguments": {},
      "dependencies": [],
      "on_failure": "abort" or "continue"
    }
  ]
}"""
        
        # Format as ChatML (Qwen-style)
        prompt = format_chat_prompt(system_prompt, user_content)
        
        logger.info("Generating plan from LLM...")
        
        # Generate with low temperature for structured output
        result = self._llm.generate_json(prompt, max_tokens=2048, temperature=0.3)
        
        if result is None:
            logger.error("Failed to extract JSON from LLM response")
            return None
        
        # Filter hallucinated tools
        if "steps" in result and isinstance(result["steps"], list):
            valid_tool_names = {t["name"] for t in available_tools}
            filtered_steps = []
            for step in result["steps"]:
                tool_name = step.get("tool_name")
                if tool_name in valid_tool_names:
                    filtered_steps.append(step)
                else:
                    logger.warning(f"Removing hallucinated tool from plan: {tool_name}")
            
            result["steps"] = filtered_steps
            
            if not result["steps"]:
                logger.warning("Plan empty after filtering hallucinations")
        
        if not self.validate_plan_schema(result):
            logger.error("Plan failed schema validation")
            return None
        
        logger.info(f"Generated plan with {len(result.get('steps', []))} steps")
        return result
    
    def validate_plan_schema(self, plan: Dict[str, Any]) -> bool:
        """Validate plan against expected schema."""
        required = ["reasoning", "steps"]
        for key in required:
            if key not in plan:
                logger.error(f"Plan missing required field: {key}")
                return False
        
        if not isinstance(plan.get("steps"), list):
            logger.error("Plan 'steps' must be a list")
            return False
        
        return True


# Global instance (lazy init)
_planner_instance: Optional[PlannerLLM] = None


def get_planner(model_path: str = None) -> PlannerLLM:
    """Get or create planner instance."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = PlannerLLM(model_path)
    return _planner_instance
