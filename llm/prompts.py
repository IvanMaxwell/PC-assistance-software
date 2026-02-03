"""
PC Automation Framework - LLM Prompts & Schemas
"""

# --- JSON Schema for Plan Output ---
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Chain-of-thought explanation"
        },
        "confidence_prediction": {
            "type": "number",
            "description": "Self-assessed confidence 0-1"
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "integer"},
                    "tool_name": {"type": "string"},
                    "arguments": {"type": "object"},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "integer"}
                    },
                    "on_failure": {
                        "type": "string",
                        "enum": ["abort", "continue"]
                    }
                },
                "required": ["step_id", "tool_name", "arguments"]
            }
        }
    },
    "required": ["reasoning", "steps"]
}


# --- System Prompts ---

PLANNER_SYSTEM_PROMPT = """You are a PC Automation Planner. Your job is to create safe, step-by-step plans to solve computer problems.

CRITICAL RULES:
1. USE ONLY TOOLS LISTED IN "AVAILABLE TOOLS". DO NOT INVENT TOOLS.
2. If the exact tool name is not in the list, DO NOT USE IT.
3. If no suitable tool exists, return an empty plan with reasoning explaining why.
4. Always include dependencies between steps.
5. For risky operations, include backup/restore point steps FIRST (only if a backup tool is available).
6. Be conservative - prefer diagnosis over destructive actions.

OUTPUT FORMAT: JSON matching the Plan Schema.
"""


VALIDATOR_SYSTEM_PROMPT = """You are a Plan Validator. Review the proposed plan for safety and correctness.

CHECK FOR:
1. Unauthorized or hallucinated tool names (CRITICAL FAIL)
2. Missing dependencies (e.g., delete before backup)
3. Risky operations without safeguards
4. Incomplete or ambiguous parameters

OUTPUT:
- "approved": true/false
- "issues": list of problems found
- "suggestions": how to fix issues
"""


def build_planner_prompt(goal: str, diagnostics: dict, tools: list, memory_context: dict) -> str:
    """Build the full prompt for the Planner LLM."""
    tools_str = "\n".join([f"- {t['name']}: {t['description']} (risk: {t['risk']})" for t in tools])
    
    return f"""{PLANNER_SYSTEM_PROMPT}

## Available Tools
{tools_str}

## Current System State
{diagnostics}

## Memory Context
Safety Rules: {memory_context.get('safety_rules', [])}
Recent Patterns: {memory_context.get('known_patterns', [])}

## User Goal
{goal}

Generate a JSON plan to achieve this goal safely.
"""


def build_validator_prompt(plan: dict, tools: list) -> str:
    """Build the full prompt for the Validator LLM."""
    import json
    return f"""{VALIDATOR_SYSTEM_PROMPT}

## Available Tools
{[t['name'] for t in tools]}

## Plan to Validate
{json.dumps(plan, indent=2)}

Validate this plan and respond with JSON.
"""
