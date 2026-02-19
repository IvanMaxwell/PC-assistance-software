"""
Summarization tool – summarise text using Gemini API.
Risk: SAFE (read-only, external API call).
"""

import os
from typing import Optional

from tools.registry import registry


def _get_gemini_model():
    """Lazy-load Gemini model to avoid import-time side effects."""
    try:
        import google.generativeai as genai
        key = os.getenv("SUMMARY_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("CM_AGENT_API_KEY")
        if not key:
            return None
        genai.configure(api_key=key)
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        return genai.GenerativeModel(model_name)
    except Exception:
        return None


@registry.register(risk_level="SAFE", category="external")
def summarize_text(text: str, max_sentences: int = 3) -> dict:
    """Summarize text into a short summary using Gemini."""
    try:
        if not text or len(text.strip()) < 20:
            return {"status": "error", "message": "Text too short to summarize"}

        model = _get_gemini_model()
        if not model:
            # Fallback: first N sentences
            sentences = text.replace("\n", " ").split(". ")
            summary = ". ".join(sentences[:max_sentences]).strip()
            if not summary.endswith("."):
                summary += "."
            return {
                "status": "success",
                "data": {"summary": summary, "method": "fallback_truncation"},
            }

        prompt = (
            f"Summarize the following text in {max_sentences} concise sentences:\n\n"
            f"{text[:4000]}"
        )
        response = model.generate_content(prompt)
        return {
            "status": "success",
            "data": {"summary": response.text.strip(), "method": "gemini"},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
