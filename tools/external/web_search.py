"""
Web search tool – search the web and retrieve snippets.
Risk: SAFE (read-only, external API call).
"""

import urllib.request
import urllib.parse
import json
from typing import Optional

from tools.registry import registry


@registry.register(risk_level="SAFE", category="external")
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web using DuckDuckGo Instant Answer API (no API key needed)."""
    try:
        if not query or not query.strip():
            return {"status": "error", "message": "Query cannot be empty"}

        encoded = urllib.parse.urlencode({"q": query, "format": "json", "no_html": "1"})
        url = f"https://api.duckduckgo.com/?{encoded}"

        req = urllib.request.Request(url, headers={"User-Agent": "PCAutomation/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = []

        # Abstract (main answer)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", "Answer"),
                "snippet": data["Abstract"],
                "url": data.get("AbstractURL", ""),
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                })

        if not results:
            return {
                "status": "success",
                "data": {"query": query, "result_count": 0, "results": [],
                         "message": "No instant results. Try a more specific query."},
            }

        return {
            "status": "success",
            "data": {"query": query, "result_count": len(results), "results": results[:max_results]},
        }
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"Network error: {e.reason}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@registry.register(risk_level="SAFE", category="external")
def fetch_webpage(url: str) -> dict:
    """Fetch text content from a URL (first 2000 chars)."""
    try:
        if not url.startswith(("http://", "https://")):
            return {"status": "error", "message": "URL must start with http:// or https://"}

        req = urllib.request.Request(url, headers={"User-Agent": "PCAutomation/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(50_000).decode("utf-8", errors="replace")

        # Strip HTML tags (basic)
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "status": "success",
            "data": {"url": url, "length": len(text), "content": text[:2000]},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
