"""
PC Automation Framework - Semantic Router
Uses Sentence Transformers to shortcut simple queries directly to tools.
"""
from typing import Dict, Any, List, Optional
import numpy as np
from core.logger import logger
from tools.registry import registry, ToolRisk

# Global router instance
_router_instance = None


class SemanticRouter:
    """
    Routes user queries directly to tools using semantic similarity.
    Bypasses the Planner LLM for simple, low-risk requests.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L12-v2", threshold: float = 0.70):
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
            # Only route to SAFE tools automatically
            if tool["risk"] != ToolRisk.SAFE.value:
                continue
                
            # Create a rich description for embedding
            # Format: "tool_name: tool_description"
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
            
        # Embed query
        query_embedding = self.model.encode([query])
        
        # Calculate cosine similarity
        # (embeddings are normalized by default in sentence_transformers?)
        # Let's assume standard cosine sim: (A . B) / (|A| |B|)
        
        # sentence-transformers util.cos_sim is better but let's stick to numpy for less deps import
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
                        "arguments": {}, # Simple tools usually have no args or inferred args - Limitation!
                        "on_failure": "abort"
                    }
                ]
            }
        
        return None


def get_router() -> Optional[SemanticRouter]:
    """Get the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        try:
            _router_instance = SemanticRouter()
        except Exception:
            return None
    return _router_instance
