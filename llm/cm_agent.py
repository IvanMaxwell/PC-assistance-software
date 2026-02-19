"""
CM Agent – Communication & Monitoring Agent (Gemini API).
Handles user-facing communication, intent classification, and execution monitoring.
"""

import os
import asyncio
from typing import Dict, Optional, List


class CMAgent:
    """
    Communication & Monitoring Agent.

    Responsibilities:
    - Classify user intent and produce a friendly acknowledgement
    - Monitor execution for drift / unexpected behaviour
    - Summarise results back to the user
    """

    def __init__(self):
        self._model = None
        self._init_gemini()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_gemini(self):
        try:
            import google.generativeai as genai
            key = os.getenv("CM_AGENT_API_KEY")
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
            
            if key:
                genai.configure(api_key=key)
                self._model = genai.GenerativeModel(model_name)
                print(f"✅ CM Agent: Gemini connected ({model_name})")
            else:
                print("⚠️ CM Agent: CM_AGENT_API_KEY not set – using fallback mode")
        except Exception as e:
            print(f"⚠️ CM Agent: Gemini unavailable ({e}) – using fallback mode")

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        return {
            "name": "CM Agent",
            "online": True,
            "backend": "gemini" if self._model else "fallback"
        }

    async def process_message(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """
        Produce a structured response with:
          - reply: short friendly acknowledgement (1 sentence)
          - explanation: natural-language breakdown of what was understood
        """
        if not self._model:
            return self._fallback_response(user_message)

        try:
            prompt = (
                "You are the CM Agent for a PC automation system. A user has sent a request.\n"
                f'User request: "{user_message}"\n\n'
                "Respond with a JSON object (no markdown) with exactly two keys:\n"
                "1. \"reply\": A single friendly sentence acknowledging the request.\n"
                "2. \"explanation\": A clear 2-4 sentence natural language explanation covering:\n"
                "   - What you understood the user wants to achieve\n"
                "   - What type of action(s) will be taken (e.g. read system info, modify files, run a process)\n"
                "   - What tools or steps are likely involved\n"
                "   - What the user can expect as an outcome\n"
                "Keep the explanation conversational and jargon-free. Do NOT use markdown inside the strings.\n"
                "Example format: {\"reply\": \"On it!\", \"explanation\": \"You want to...\"}"
            )
            import json
            response = await asyncio.to_thread(self._model.generate_content, prompt)
            text = response.text.strip()
            # Strip markdown code fences if present
            if "```" in text:
                text = text.split("```")[1].split("```")[0]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text.strip())
            # Ensure both keys exist
            return {
                "reply": result.get("reply", "Got it, working on it!"),
                "explanation": result.get("explanation", ""),
            }
        except Exception:
            return self._fallback_response(user_message)

    async def explain_query(self, user_message: str) -> str:
        """
        Standalone method: returns only the natural-language explanation of a query.
        Useful for on-demand calls without triggering a full process_message cycle.
        """
        result = await self.process_message(user_message)
        return result.get("explanation", "")

    async def classify_intent(self, user_message: str) -> Dict:
        """Return structured intent dict from user message."""
        if not self._model:
            return {"intent": user_message, "category": "general", "confidence": 0.5}

        try:
            prompt = (
                "Classify this PC automation request into a JSON object with keys: "
                "intent (short verb-noun), category (system/files/process/network/external), "
                f"confidence (0-1).\n\nRequest: \"{user_message}\"\nJSON:"
            )
            resp = await asyncio.to_thread(self._model.generate_content, prompt)
            import json
            text = resp.text.strip()
            if "```" in text:
                text = text.split("```")[1].split("```")[0]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception:
            return {"intent": user_message, "category": "general", "confidence": 0.5}

    async def monitor_step(self, step_result: Dict) -> Dict:
        """Check a step result for drift or unexpected behaviour."""
        status = step_result.get("status", "unknown")
        if status == "error":
            return {
                "drift_detected": True,
                "severity": "high",
                "message": f"Step failed: {step_result.get('message', 'unknown error')}",
                "recommendation": "pause",
            }
        return {"drift_detected": False}

    async def summarize_execution(self, results: List[Dict], user_input: str = "") -> str:
        """Summarise completed execution results for the user in context of their request."""
        successes = sum(1 for r in results if r.get("status") == "success")
        failures = len(results) - successes

        if not self._model:
            if failures == 0:
                return f"All {successes} steps completed successfully."
            return f"Completed {successes}/{len(results)} steps. {failures} failed."

        try:
            import json
            # Include the original query so the AI can provide a contextual summary
            prompt = (
                "You are an AI assistant summarizing PC automation results.\n"
                f"User original request: \"{user_input}\"\n"
                "Execution results:\n"
                f"{json.dumps(results, default=str)[:3000]}\n\n"
                "Task: Provide a 1-2 sentence friendly summary of what was done and the final outcome.\n"
                "If the data contains specific numbers (like CPU %, file counts), mention them briefly.\n"
                "Do NOT use markdown. Keep it conversational."
            )
            resp = await asyncio.to_thread(self._model.generate_content, prompt)
            return resp.text.strip()
        except Exception as e:
            print(f"⚠️ CM Agent summary error: {e}")
            if failures == 0:
                if successes == 1:
                    return f"Successfully completed the requested task."
                return f"All {successes} steps were executed successfully."
            return f"The task was partially completed ({successes}/{len(results)} steps successful). {failures} steps failed to execute."

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_response(message: str) -> Dict:
        msg = message.lower()
        if any(w in msg for w in ("cpu", "memory", "ram", "disk", "system")):
            return {
                "reply": "I'll check your system status right away.",
                "explanation": f"You want to get information about your system's hardware performance. I'll read the current CPU, memory, or disk metrics and report them back to you. No changes will be made to your system — this is a read-only diagnostic.",
            }
        if any(w in msg for w in ("file", "organiz", "download", "folder")):
            return {
                "reply": "I'll help you manage your files.",
                "explanation": f"You want to perform a file-related operation. I'll look at the relevant directory, identify the files matching your request, and carry out the action (such as listing, searching, or organising). Your files will only be modified if the action explicitly requires it.",
            }
        if any(w in msg for w in ("process", "kill", "running")):
            return {
                "reply": "I'll look at your running processes.",
                "explanation": f"You want to inspect or control a running process on your system. I'll list the active processes, identify the one you're referring to, and take the requested action such as viewing details or terminating it.",
            }
        if any(w in msg for w in ("network", "internet", "dns", "connect")):
            return {
                "reply": "I'll diagnose your network connection.",
                "explanation": f"You want to check your network status. I'll test your internet connectivity, inspect your network configuration, or run a DNS check depending on what you need. The results will tell you whether your connection is healthy.",
            }
        return {
            "reply": f"I'll help you with that.",
            "explanation": f"You asked: \"{message}\". I'll analyse your request, determine the best tools to use, and execute the necessary steps to get you the result you need.",
        }

