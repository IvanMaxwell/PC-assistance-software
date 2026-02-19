"""
PC Automation Framework - Tool System
Auto-discovers and registers all tools from diagnostics/ and actions/ subpackages.
"""

from tools.registry import registry

def discover_tools():
    """Import all tool modules to trigger @registry.register decorators."""
    # Diagnostics (SAFE)
    try:
        from tools.diagnostics import system_tools
        from tools.diagnostics import process_tools
        from tools.diagnostics import network_tools
        from tools.diagnostics import file_tools
    except ImportError as e:
        print(f"⚠️ Diagnostic tool import error: {e}")

    # Actions (MEDIUM/HIGH)
    try:
        from tools.actions import file_actions
        from tools.actions import process_actions
        from tools.actions import network_actions
        from tools.actions import document_tools  # Class-based
    except ImportError as e:
        print(f"⚠️ Action tool import error: {e}")

    # External (SAFE)
    try:
        from tools.external import web_search
        from tools.external import summarization
        from tools.external import content_tools  # Class-based
    except ImportError as e:
        print(f"⚠️ External tool import error: {e}")

    print(f"✅ {len(registry.get_all())} tools registered")

__all__ = ["registry", "discover_tools"]
