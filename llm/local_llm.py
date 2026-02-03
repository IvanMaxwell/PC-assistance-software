"""
PC Automation Framework - Local LLM Interface (llama.cpp)
"""
import json
import re
from typing import Optional, Dict, Any, List
from llama_cpp import Llama
from core.logger import logger


class LocalLLM:
    """
    Wrapper for local LLM using llama-cpp-python.
    Handles model loading, prompt formatting, and JSON extraction.
    """
    
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        verbose: bool = False
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self._model: Optional[Llama] = None
        self._verbose = verbose
    
    def load(self):
        """Load the model into memory."""
        if self._model is not None:
            logger.info("Model already loaded")
            return
        
        logger.info(f"Loading model: {self.model_path}")
        
        try:
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=self._verbose
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def unload(self):
        """Unload model from memory."""
        if self._model:
            del self._model
            self._model = None
            logger.info("Model unloaded")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: List[str] = None
    ) -> str:
        """Generate text from prompt."""
        if self._model is None:
            self.load()
        
        logger.debug(f"Generating with {len(prompt)} char prompt")
        
        stop_tokens = stop if stop else ["</s>", "<|im_end|>"]
        
        response = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_tokens
        )
        
        text = response["choices"][0]["text"]
        logger.debug(f"Generated {len(text)} chars")
        return text
    
    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3
    ) -> Optional[Dict[str, Any]]:
        """Generate and parse JSON response."""
        text = self.generate(prompt, max_tokens, temperature)
        return self.extract_json(text)
    
    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response text."""
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1)
        
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}")
        
        return None


def format_chat_prompt(system: str, user: str) -> str:
    """Format prompt in ChatML style for Qwen-based models."""
    return f"""<|im_start|>system
{system}<|im_end|>
<|im_start|>user
{user}<|im_end|>
<|im_start|>assistant
"""

