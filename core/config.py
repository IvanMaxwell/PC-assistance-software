"""
PC Automation Framework - Configuration
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import os

# --- FSM States ---
class State(Enum):
    IDLE = "idle"
    NEGOTIATING = "negotiating"
    DIAGNOSING = "diagnosing"
    PLANNING = "planning"
    SCORING = "scoring"
    VALIDATING = "validating"
    EXECUTING = "executing"
    LEARNING = "learning"
    ERROR_RECOVERY = "error_recovery"


# --- API Configuration ---
@dataclass
class APIConfig:
    """Holds API keys and endpoints."""
    # Local LLM (Planner/Validator) - Deepseek R1 Distill
    local_model_path: str = os.getenv(
        "LOCAL_MODEL_PATH", 
        r"C:\Users\Home\Desktop\final year project\documents\Orchestration-O1\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
    )
    
    # Fast API (Analysis, Content)
    fast_api_key: Optional[str] = os.getenv("FAST_API_KEY")
    fast_api_base: str = os.getenv("FAST_API_BASE", "https://api.openai.com/v1")
    fast_api_model: str = os.getenv("FAST_API_MODEL", "gpt-4o-mini")
    
    # Dev/Coder API (Code Generation - Mock for now)
    dev_api_key: Optional[str] = os.getenv("DEV_API_KEY")
    dev_api_base: str = os.getenv("DEV_API_BASE", "https://api.anthropic.com/v1")
    dev_api_model: str = os.getenv("DEV_API_MODEL", "claude-3-5-sonnet-20241022")
    dev_api_mock: bool = True  # Set to False when ready to use real API


# --- Confidence Thresholds ---
CONFIDENCE_THRESHOLD = 0.8  # Plans below this go to Validator
HIGH_RISK_TOOL_PENALTY = 0.15
AMBIGUITY_PENALTY = 0.1


# --- Logging ---
LOG_DIR = "./data/logs"
LOG_LEVEL = "INFO"


# --- Memory ---
MEMORY_VECTOR_DIR = "./data/memory_vector"
SHORT_TERM_MAX_ITEMS = 50


# --- Singleton Config Instance ---
config = APIConfig()
