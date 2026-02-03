"""
PC Automation Framework - External API Interface
Wraps interactions with Fast (OpenAI-compatible) and Dev (Claude-compatible) APIs.
"""
import requests
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from core.config import config
from core.logger import logger


class ExternalAPI:
    """Generic wrapper for external LLM APIs."""
    
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
    
    def generate(self, system: str, user: str, temperature: float = 0.7) -> str:
        """Call the API."""
        raise NotImplementedError


class FastAPIWrapper(ExternalAPI):
    """Wrapper for 'Fast' API (e.g., GPT-4o-mini) for data analysis/search."""
    
    def generate(self, system: str, user: str, temperature: float = 0.7) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature
        }
        
        try:
            # Handle OpenAI-compatible endpoints
            url = f"{self.base_url}/chat/completions"
            if self.base_url.endswith("/v1"):
                 url = f"{self.base_url}/chat/completions"
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"FastAPI Call Failed: {e}")
            return f"Error: {str(e)}"


class DevAPIWrapper(ExternalAPI):
    """Wrapper for 'Dev' API (e.g., Claude 3.5 Sonnet) for coding."""
    
    def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        # Mock implementation if configured
        if config.dev_api_mock:
            logger.info("DevAPI (Mock) called")
            return "print('Hello from Mock Dev API')"
            
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "system": system,
            "messages": [
                {"role": "user", "content": user}
            ],
            "max_tokens": 4096,
            "temperature": temperature
        }
        
        try:
            url = f"{self.base_url}/messages"
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            logger.error(f"DevAPI Call Failed: {e}")
            return f"Error: {str(e)}"


# Global instances
_fast_api: Optional[FastAPIWrapper] = None
_dev_api: Optional[DevAPIWrapper] = None


def get_fast_api() -> FastAPIWrapper:
    global _fast_api
    if not _fast_api:
        _fast_api = FastAPIWrapper(
            base_url=config.fast_api_base,
            api_key=config.fast_api_key or "mock-key",
            model=config.fast_api_model
        )
    return _fast_api


def get_dev_api() -> DevAPIWrapper:
    global _dev_api
    if not _dev_api:
        _dev_api = DevAPIWrapper(
            base_url=config.dev_api_base,
            api_key=config.dev_api_key or "mock-key",
            model=config.dev_api_model
        )
    return _dev_api
