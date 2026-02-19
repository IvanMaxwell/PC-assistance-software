"""
Content Consumption & Information Retrieval Tools (class-based).

Provides tools for:
- Opening URLs, YouTube, Spotify, Instagram, local media
- Web search summarization (using existing web_search tool output)
- Fetching and summarizing web pages
- Reading and summarizing local documents
"""

import os
import subprocess
import urllib.request
import urllib.parse
import re
import asyncio
from typing import Optional

from tools.registry import registry, ToolMeta
import inspect


def _extract_params(method):
    sig = inspect.signature(method)
    params = []
    for pname, param in sig.parameters.items():
        if pname == "self":
            continue
        ptype = "string"
        if param.annotation != inspect.Parameter.empty:
            ptype = getattr(param.annotation, "__name__", str(param.annotation))
        params.append({
            "name": pname,
            "type": ptype,
            "required": param.default is inspect.Parameter.empty,
            "default": None if param.default is inspect.Parameter.empty else param.default,
        })
    return params


class ContentTools:
    """
    Class-based tool group for content consumption and information retrieval.
    Shares a single Gemini client for all summarization methods.
    """

    def __init__(self):
        self._gemini = None
        self._init_gemini()
        self._register()

    def _init_gemini(self):
        try:
            import google.generativeai as genai
            key = os.getenv("GEMINI_API_KEY") or os.getenv("CM_AGENT_API_KEY")
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
            if key:
                genai.configure(api_key=key)
                self._gemini = genai.GenerativeModel(model_name)
        except Exception:
            pass

    def _register(self):
        """Register all public methods as tools."""
        tool_defs = [
            ("open_url",           "SAFE",   "content"),
            ("open_youtube",       "SAFE",   "content"),
            ("open_spotify",       "SAFE",   "content"),
            ("open_instagram",     "SAFE",   "content"),
            ("play_local_media",   "SAFE",   "content"),
            ("open_local_file",    "SAFE",   "content"),
            ("fetch_webpage_text", "SAFE",   "content"),
            ("summarize_url",      "SAFE",   "content"),
            ("summarize_web_search", "SAFE", "content"),
            ("read_document",      "SAFE",   "content"),
            ("summarize_document", "SAFE",   "content"),
        ]
        for name, risk, category in tool_defs:
            method = getattr(self, name)
            doc = (method.__doc__ or "").strip().split("\n")[0]
            meta = ToolMeta(
                name=name,
                func=method,
                risk_level=risk,
                category=category,
                description=doc,
                parameters=_extract_params(method),
            )
            registry._tools[name] = meta

    # ------------------------------------------------------------------
    # Content Consumption
    # ------------------------------------------------------------------

    def open_url(self, url: str) -> dict:
        """Open any URL in the default web browser."""
        try:
            import webbrowser
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return {"status": "success", "data": {"url": url, "action": "opened in browser"}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_youtube(self, query: str) -> dict:
        """Open a YouTube search or video URL in the default browser."""
        try:
            import webbrowser
            if query.startswith("http"):
                url = query
            else:
                encoded = urllib.parse.quote_plus(query)
                url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(url)
            return {"status": "success", "data": {"url": url, "query": query}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_spotify(self, query: str) -> dict:
        """Open a Spotify search in the browser or Spotify app."""
        try:
            import webbrowser
            if query.startswith("spotify:") or query.startswith("http"):
                url = query
            else:
                encoded = urllib.parse.quote_plus(query)
                url = f"https://open.spotify.com/search/{encoded}"
            webbrowser.open(url)
            return {"status": "success", "data": {"url": url, "query": query}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_instagram(self, username_or_url: str) -> dict:
        """Open an Instagram profile or post in the default browser."""
        try:
            import webbrowser
            if username_or_url.startswith("http"):
                url = username_or_url
            else:
                handle = username_or_url.lstrip("@")
                url = f"https://www.instagram.com/{handle}/"
            webbrowser.open(url)
            return {"status": "success", "data": {"url": url}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def play_local_media(self, file_path: str) -> dict:
        """Open a local audio or video file with the default media player."""
        try:
            from pathlib import Path
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            if os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return {"status": "success", "data": {"file": str(p), "action": "opened with default player"}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_local_file(self, file_path: str) -> dict:
        """Open any local file with its default application."""
        try:
            from pathlib import Path
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            if os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return {"status": "success", "data": {"file": str(p), "action": "opened"}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Web Fetching & Summarization
    # ------------------------------------------------------------------

    def fetch_webpage_text(self, url: str, max_chars: int = 4000) -> dict:
        """Fetch a webpage and return clean plain text (HTML stripped)."""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (PC Automation Framework)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return {
                "status": "success",
                "data": {
                    "url": url,
                    "text": text[:max_chars],
                    "truncated": len(text) > max_chars,
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def summarize_url(self, url: str) -> dict:
        """Fetch a webpage and return a Gemini-generated 3-5 sentence summary."""
        fetch = self.fetch_webpage_text(url)
        if fetch["status"] != "success":
            return fetch
        text = fetch["data"]["text"]
        if not self._gemini:
            return {"status": "success", "data": {"url": url, "summary": text[:500]}}
        try:
            prompt = (
                f"Summarize the following webpage content in 3-5 clear sentences.\n"
                f"URL: {url}\n\nContent:\n{text[:3000]}"
            )
            resp = self._gemini.generate_content(prompt)
            return {"status": "success", "data": {"url": url, "summary": resp.text.strip()}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def summarize_web_search(self, query: str) -> dict:
        """Search the web and return a Gemini-generated summary of the top results."""
        try:
            # Use existing web_search tool
            from tools.registry import registry as reg
            import asyncio
            loop = asyncio.new_event_loop()
            search_result = loop.run_until_complete(reg.execute("web_search", {"query": query}))
            loop.close()

            if search_result.get("status") != "success":
                return search_result

            results = search_result.get("data", {}).get("results", [])
            if not results:
                return {"status": "error", "message": "No search results found"}

            snippets = "\n".join(
                f"- {r.get('title', '')}: {r.get('snippet', '')}"
                for r in results[:5]
            )

            if not self._gemini:
                return {"status": "success", "data": {"query": query, "summary": snippets}}

            prompt = (
                f'Summarize these web search results for "{query}" in 3-5 sentences, '
                f"like a Chrome AI overview. Be factual and concise.\n\n{snippets}"
            )
            resp = self._gemini.generate_content(prompt)
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "summary": resp.text.strip(),
                    "sources": [r.get("url", "") for r in results[:5]],
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Local Document Reading & Summarization
    # ------------------------------------------------------------------

    def read_document(self, file_path: str, max_chars: int = 5000) -> dict:
        """Read a local text file (.txt, .md, .csv, .json, .py, etc.) and return its content."""
        try:
            from pathlib import Path
            p = Path(file_path).expanduser().resolve()
            if not p.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}
            text = p.read_text(encoding="utf-8", errors="replace")
            return {
                "status": "success",
                "data": {
                    "file": str(p),
                    "extension": p.suffix,
                    "content": text[:max_chars],
                    "truncated": len(text) > max_chars,
                    "total_chars": len(text),
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def summarize_document(self, file_path: str) -> dict:
        """Read a local document and return a Gemini-generated summary."""
        read = self.read_document(file_path)
        if read["status"] != "success":
            return read
        content = read["data"]["content"]
        fname = read["data"]["file"]
        if not self._gemini:
            return {"status": "success", "data": {"file": fname, "summary": content[:500]}}
        try:
            prompt = (
                f"Summarize the following document in 3-5 sentences.\n"
                f"File: {fname}\n\nContent:\n{content[:3000]}"
            )
            resp = self._gemini.generate_content(prompt)
            return {"status": "success", "data": {"file": fname, "summary": resp.text.strip()}}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Module-level singleton — instantiation triggers registration
content_tools = ContentTools()
