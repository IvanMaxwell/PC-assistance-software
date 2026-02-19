"""
CS Agent – Counterfactual Simulation Agent (Gemini API).
Evaluates plans for risks, simulates outcomes, and suggests safer alternatives.
"""

import os
import asyncio
import json
from typing import Dict, List, Optional


class CSAgent:
    """
    Counterfactual Simulation Agent.

    Responsibilities:
    - Evaluate execution plans for potential risks
    - Suggest safer alternatives when risk is detected
    - Provide go/no-go recommendation
    """

    def __init__(self):
        self._model = None
        self._init_gemini()

    def _init_gemini(self):
        try:
            import google.generativeai as genai
            key = os.getenv("CS_AGENT_API_KEY")
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
            
            if key:
                genai.configure(api_key=key)
                self._model = genai.GenerativeModel(model_name)
                print(f"✅ CS Agent: Gemini connected ({model_name})")
            else:
                print("⚠️ CS Agent: CS_AGENT_API_KEY not set – using rule-based mode")
        except Exception as e:
            print(f"⚠️ CS Agent: Gemini unavailable ({e}) – using rule-based mode")

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        return {
            "name": "CS Agent",
            "online": True,
            "backend": "gemini" if self._model else "rules"
        }

    async def evaluate_plan(self, plan: Dict) -> Dict:
        """
        Evaluate a plan and return risk assessment.

        Returns dict with:
            risk_level: LOW | MEDIUM | HIGH
            concerns: List[str]
            alternatives: List[str]
            recommendation: APPROVE | APPROVE_WITH_MODIFICATIONS | REJECT
        """
        steps = plan.get("steps", [])
        if not steps:
            return self._make_result("LOW", [], [], "APPROVE")

        # Rule-based quick check first
        rule_result = self._rule_based_eval(steps)

        # If Gemini available and risk >= MEDIUM, get deeper analysis
        if self._model and rule_result["risk_level"] != "LOW":
            try:
                return await self._gemini_eval(steps, rule_result)
            except Exception:
                pass  # Fall through to rule-based

        return rule_result

    async def evaluate_step(self, step: Dict) -> Dict:
        """Evaluate a single step's risk."""
        return self._rule_based_eval([step])

    # ------------------------------------------------------------------
    # Rule-based evaluation (always available)
    # ------------------------------------------------------------------

    _HIGH_RISK_TOOLS = {"kill_process", "proc.kill", "fs.delete_file", "delete_old_files"}
    _MEDIUM_RISK_TOOLS = {"organize_downloads", "flush_dns", "clear_temp_files",
                          "reset_network_adapter", "bulk_rename_files"}

    def _rule_based_eval(self, steps: List[Dict]) -> Dict:
        concerns = []
        alternatives = []
        risk = "LOW"

        for step in steps:
            tool = step.get("tool", "")
            desc = step.get("description", "").lower()

            if tool in self._HIGH_RISK_TOOLS or "delete" in tool or "kill" in tool:
                risk = "HIGH"
                concerns.append(f"'{tool}' can cause data loss or crash applications")
                alternatives.append(f"Consider using dry_run=True first for '{tool}'")

            elif tool in self._MEDIUM_RISK_TOOLS or "flush" in tool or "rename" in tool:
                if risk != "HIGH":
                    risk = "MEDIUM"
                concerns.append(f"'{tool}' modifies system state")

            if "all" in desc and ("delete" in desc or "kill" in desc or "remove" in desc):
                risk = "HIGH"
                concerns.append("Bulk destructive operation detected")
                alternatives.append("Consider limiting scope or using dry_run first")

        recommendation = {
            "LOW": "APPROVE",
            "MEDIUM": "APPROVE_WITH_MODIFICATIONS" if alternatives else "APPROVE",
            "HIGH": "APPROVE_WITH_MODIFICATIONS" if alternatives else "REJECT",
        }[risk]

        return self._make_result(risk, concerns, alternatives, recommendation)

    # ------------------------------------------------------------------
    # Gemini-powered deep evaluation
    # ------------------------------------------------------------------

    async def _gemini_eval(self, steps: List[Dict], rule_result: Dict) -> Dict:
        steps_text = "\n".join(
            f"- {s.get('tool', '?')}: {s.get('description', '')}" for s in steps
        )
        prompt = (
            "You are the CS Agent (Counterfactual Simulation) for a PC automation system.\n"
            "Evaluate this execution plan for risks.\n\n"
            f"Steps:\n{steps_text}\n\n"
            f"Initial risk assessment: {rule_result['risk_level']}\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"risk_level":"LOW|MEDIUM|HIGH",'
            '"concerns":["..."],'
            '"alternatives":["..."],'
            '"recommendation":"APPROVE|APPROVE_WITH_MODIFICATIONS|REJECT"}\n'
        )

        resp = await asyncio.to_thread(self._model.generate_content, prompt)
        text = resp.text.strip()
        if "```" in text:
            text = text.split("```")[1].split("```")[0]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())

        # Validate keys
        for key in ("risk_level", "concerns", "recommendation"):
            if key not in parsed:
                return rule_result
        parsed.setdefault("alternatives", [])
        return parsed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_result(risk: str, concerns: list, alternatives: list, recommendation: str) -> Dict:
        return {
            "risk_level": risk,
            "concerns": concerns,
            "alternatives": alternatives,
            "recommendation": recommendation,
        }
