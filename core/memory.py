"""
PC Automation Framework - Memory Management
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from core.config import MEMORY_VECTOR_DIR, SHORT_TERM_MAX_ITEMS
from core.logger import logger


@dataclass
class MemoryEntry:
    """A single memory entry."""
    timestamp: str
    category: str  # "execution", "error", "success_pattern"
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)


class ShortTermMemory:
    """
    In-session memory. Cleared when session ends.
    Holds current execution context and recent results.
    """
    
    def __init__(self, max_items: int = SHORT_TERM_MAX_ITEMS):
        self.max_items = max_items
        self._entries: List[MemoryEntry] = []
    
    def add(self, category: str, content: Dict[str, Any], tags: List[str] = None):
        """Add an entry to short-term memory."""
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            category=category,
            content=content,
            tags=tags or []
        )
        self._entries.append(entry)
        
        # Enforce limit
        if len(self._entries) > self.max_items:
            self._entries.pop(0)
        
        logger.debug(f"Short-term memory: Added {category} entry")
    
    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        """Get n most recent entries."""
        return self._entries[-n:]
    
    def get_by_category(self, category: str) -> List[MemoryEntry]:
        """Get entries by category."""
        return [e for e in self._entries if e.category == category]
    
    def clear(self):
        """Clear all short-term memory."""
        self._entries = []
        logger.info("Short-term memory cleared")


class LongTermMemory:
    """
    Persistent memory. Stored on disk.
    Contains curated safety rules and promoted patterns.
    """
    
    def __init__(self, storage_dir: str = MEMORY_VECTOR_DIR):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._safety_rules_file = os.path.join(storage_dir, "safety_rules.json")
        self._patterns_file = os.path.join(storage_dir, "patterns.json")
    
    def get_safety_rules(self) -> List[str]:
        """Get curated safety rules."""
        if os.path.exists(self._safety_rules_file):
            with open(self._safety_rules_file, "r") as f:
                return json.load(f)
        
        # Default safety rules
        return [
            "Never delete system files without explicit backup",
            "Always create restore point before registry changes",
            "Halt execution if admin rights are required but not granted",
            "Do not modify network settings without user confirmation"
        ]
    
    def add_safety_rule(self, rule: str):
        """Add a new safety rule (human-curated)."""
        rules = self.get_safety_rules()
        if rule not in rules:
            rules.append(rule)
            with open(self._safety_rules_file, "w") as f:
                json.dump(rules, f, indent=2)
            logger.info(f"Added safety rule: {rule}")
    
    def get_success_patterns(self) -> List[Dict[str, Any]]:
        """Get successful resolution patterns."""
        if os.path.exists(self._patterns_file):
            with open(self._patterns_file, "r") as f:
                return json.load(f)
        return []
    
    def promote_pattern(self, pattern: Dict[str, Any]):
        """Promote a successful pattern to long-term memory."""
        patterns = self.get_success_patterns()
        patterns.append({
            "added": datetime.now().isoformat(),
            **pattern
        })
        with open(self._patterns_file, "w") as f:
            json.dump(patterns, f, indent=2)
        logger.info("Promoted pattern to long-term memory")


class MemoryManager:
    """
    Unified interface for all memory operations.
    """
    
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
    
    def store_execution_result(self, result: Dict[str, Any]):
        """Store an execution result in short-term memory."""
        self.short_term.add("execution", result)
    
    def get_context_for_planner(self) -> Dict[str, Any]:
        """Get memory context to send to Planner LLM."""
        return {
            "recent_executions": [
                e.content for e in self.short_term.get_recent(5)
            ],
            "safety_rules": self.long_term.get_safety_rules(),
            "known_patterns": self.long_term.get_success_patterns()[-5:]
        }


# Global instance
memory = MemoryManager()
