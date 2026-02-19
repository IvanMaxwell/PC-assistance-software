"""
PC Automation Framework - Semantic Router
Uses Sentence Transformers to shortcut simple queries directly to tools.
"""
from typing import Dict, Any, List, Optional
import numpy as np
from core.logger import logger
from tools.registry import registry


# Global router instance
_router_instance = None


class SemanticRouter:
    """
    Routes user queries directly to tools using semantic similarity.
    Bypasses the Planner LLM for simple, low-risk requests.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L12-v2", threshold: float = 0.47):
        self.threshold = threshold
        self.model = None
        self.model_name = model_name
        self.tool_embeddings = {}
        self.tool_map = {}
        self._load_model()
        self._index_tools()
        
    def _load_model(self):
        """Lazy load the sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading Semantic Router model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Router model loaded.")
        except ImportError:
            logger.error("sentence-transformers not installed. Router disabled.")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load router model: {e}")
            self.model = None

    def _index_tools(self):
        """Compute embeddings for all registered Safe tools."""
        if not self.model:
            return
            
        tools = registry.list_tools()
        self.tool_map = {}
        descriptions = []
        
        for tool in tools:
            # Only shortcut SAFE tools that have NO required parameters
            if tool["risk"] != "safe":
                continue
                
            if len(tool.get("params", [])) > 0:
                continue
                
            desc = f"{tool['name']}: {tool['description']}"
            descriptions.append(desc)
            self.tool_map[len(descriptions)-1] = tool["name"]
            
        if descriptions:
            self.tool_embeddings = self.model.encode(descriptions)
            logger.info(f"Indexed {len(descriptions)} tools for semantic routing")

    def find_tool(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Find a matching tool for the query.
        Returns plan dict if match found > threshold, else None.
        """
        if not self.model or len(self.tool_embeddings) == 0:
            return None
            
        query_embedding = self.model.encode([query])
        
        from sentence_transformers import util
        hits = util.semantic_search(query_embedding, self.tool_embeddings, top_k=1)
        
        if not hits or not hits[0]:
            return None
            
        best_hit = hits[0][0]
        score = best_hit['score']
        idx = best_hit['corpus_id']
        tool_name = self.tool_map.get(idx)
        
        logger.info(f"Router check: '{query}' -> '{tool_name}' (Score: {score:.2f})")
        
        if score >= self.threshold:
            logger.info(f"Router Hit! Bypassing planner for: {tool_name}")
            return {
                "reasoning": f"Semantic Match ({score:.2f}) shortcut",
                "confidence_prediction": float(score),
                "steps": [
                    {
                        "step_id": 1,
                        "tool_name": tool_name,
                        "arguments": {},
                        "on_failure": "abort"
                    }
                ]
            }
        
        return None


    def get_similarity_scores(self, query: str, top_k: int = 5) -> List[Dict]:
        """Return top-k tool similarity scores for a query (for UI display)."""
        if not self.model or len(self.tool_embeddings) == 0:
            return []
        query_embedding = self.model.encode([query])
        from sentence_transformers import util
        hits = util.semantic_search(query_embedding, self.tool_embeddings, top_k=top_k)
        results = []
        if hits and hits[0]:
            for hit in hits[0]:
                idx = hit['corpus_id']
                results.append({
                    "tool": self.tool_map.get(idx, "?"),
                    "score": round(hit['score'], 3),
                })
        return results


def get_router() -> Optional[SemanticRouter]:
    """Get the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        try:
            _router_instance = SemanticRouter()
        except Exception:
            return None
    return _router_instance
