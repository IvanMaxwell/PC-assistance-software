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
    args = parser.parse_args()
    
    user_request = " ".join(args.request)
    model_path = args.model or config.local_model_path
    
    logger.info("=" * 60)
    logger.info("PC Automation Framework Starting...")
    logger.info("=" * 60)
    
    # Show registered tools
    tools = registry.list_tools()
    logger.info(f"Registered {len(tools)} tools:")
    for tool in tools:
        logger.info(f"  - {tool['name']} ({tool['risk']})")
    
    logger.info(f"Model: {model_path}")
    logger.info(f"Request: {user_request}")
    logger.info("=" * 60)
    
    # Create orchestrator
    orchestrator = Orchestrator(model_path=model_path)
    
    try:
        # Run orchestrator
        results = orchestrator.run(user_request)
        
        logger.info("=" * 60)
        logger.info("Execution Complete")
        logger.info(f"Results: {results}")
        logger.info("=" * 60)
        
        return results
    finally:
        # Cleanup (unload model)
        orchestrator.cleanup()


if __name__ == "__main__":
    main()
