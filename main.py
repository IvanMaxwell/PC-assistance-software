"""
PC Automation Framework - Entry Point
"""
import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.orchestrator import Orchestrator
from core.logger import logger
from core.config import config
from core.display import display
from tools.registry import registry

# Import diagnostic tools to register them
import tools.diagnostics.system_tools
import tools.diagnostics.advanced_tools
import tools.actions.active_tools
import tools.actions.external_tools


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PC Automation Framework")
    parser.add_argument("request", nargs="*", default=["Check system status"],
                        help="User request to process")
    parser.add_argument("--model", "-m", type=str, default=None,
                        help="Path to GGUF model file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without executing")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show verbose output")
    args = parser.parse_args()
    
    user_request = " ".join(args.request)
    model_path = args.model or config.local_model_path
    
    # Show header
    display.header()
    
    # Show registered tools (compact)
    tools = registry.list_tools()
    if args.verbose:
        display.show_tools(tools)
    else:
        display.console.print(f"[dim]Loaded {len(tools)} tools[/dim]")
    
    # Show user request
    display.show_request(user_request)
    display.divider()
    
    # Create orchestrator with display
    orchestrator = Orchestrator(model_path=model_path, display=display)
    
    try:
        # Run orchestrator
        results = orchestrator.run(user_request)
        
        display.divider()
        display.show_results(results)
        
        return results
    except KeyboardInterrupt:
        display.show_error("Interrupted by user")
    except Exception as e:
        display.show_error(str(e))
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        # Cleanup (unload model)
        orchestrator.cleanup()


if __name__ == "__main__":
    main()
