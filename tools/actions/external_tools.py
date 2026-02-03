"""
PC Automation Framework - External API Tools
"""
import os
import uuid
from typing import Dict, Any
from tools.registry import registry, ToolRisk
from llm.api_wrapper import get_fast_api, get_dev_api
from core.logger import logger


@registry.register(
    name="net.access_ext",
    description="Ask External AI for information (Internet access)",
    risk_level=ToolRisk.MEDIUM,
    required_params=["query"]
)
def access_external_knowledge(query: str) -> Dict[str, Any]:
    """
    Query the 'Fast' External API (e.g., GPT-4o) for information.
    Use this when you need data not on the local PC (e.g., latest drivers, error codes).
    """
    try:
        api = get_fast_api()
        system = "You are a helper for a PC automation agent. Answer the query concisely using your knowledge base."
        response = api.generate(system, query)
        return {
            "query": query,
            "response": response
        }
    except Exception as e:
        return {"error": f"API call failed: {e}"}


@registry.register(
    name="net.download_ext",
    description="Generate a script to download/install files (Requires Review)",
    risk_level=ToolRisk.HIGH,
    required_params=["goal", "url"]
)
def generate_download_script(goal: str, url: str) -> Dict[str, Any]:
    """
    Generate a Python script via 'Dev' External API to perform a download/install task.
    The script is saved to a temp folder and MUST be reviewed by the user before running.
    """
    try:
        api = get_dev_api()
        system = """You are a Python expert. Write a robust script to perform the requested download/install task.
RULES:
1. Use 'requests' for downloading
2. Show progress (print)
3. Verify file size/integrity if possible
4. Save to %TEMP%
5. No destructive actions
6. Code ONLY, no markdown, no comments outside the code.
"""
        prompt = f"Goal: {goal}\nURL: {url}\nWrite a standalone python script."
        
        script_content = api.generate(system, prompt)
        
        # Save script
        script_id = uuid.uuid4().hex[:8]
        filename = f"script_{script_id}.py"
        save_path = os.path.join(os.getcwd(), "generated_scripts", filename)
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w") as f:
            f.write(script_content)
            
        return {
            "status": "generated",
            "message": f"Script generated for review. NOT EXECUTED.",
            "script_path": save_path,
            "preview": script_content[:200] + "..."
        }
    except Exception as e:
        return {"error": f"Dev API call failed: {e}"}
