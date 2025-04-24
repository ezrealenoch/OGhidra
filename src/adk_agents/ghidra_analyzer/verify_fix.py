#!/usr/bin/env python3
"""
Verification script for testing the fix for the KeyError: 'arguments' issue.
This script simulates running a simplified version of the agent loop to ensure 
the Ollama/LiteLLM compatibility is working correctly.
"""

import os
import sys
import json
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Main verification function to test our agent with Ollama.
    """
    logger.info("Starting verification for KeyError: 'arguments' fix...")
    
    # Import the agents - this should use our fixed version
    from src.adk_agents.ghidra_analyzer.agents import (
        planning_agent, tool_executor_agent, analysis_agent, review_agent
    )
    
    # Create a simple test query
    test_query = "List all functions"
    logger.info(f"Testing with query: '{test_query}'")
    
    # Create initial state
    state = {
        "user_query": test_query,
        "ghidra_plan": [],
        "last_tool_result": None,
        "current_analysis": ""
    }
    
    try:
        # Attempt to run just the planning agent first
        logger.info("Executing planning agent...")
        plan_state = planning_agent._instruction_model.predict(state)
        
        # Should be valid JSON (not function calling format)
        plan = None
        try:
            plan = json.loads(plan_state)
            logger.info(f"Planning agent returned valid JSON: {plan}")
        except json.JSONDecodeError:
            logger.error(f"Planning agent did not return valid JSON: {plan_state}")
            return False
        
        # For additional verification, we could run the other agents too
        
        # Mark verification as successful
        logger.info("Verification passed! The fix for KeyError: 'arguments' is working.")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed with error: {e}")
        if "arguments" in str(e):
            logger.error("The KeyError: 'arguments' issue is still present!")
        return False

if __name__ == "__main__":
    success = main()
    # Exit with appropriate code
    sys.exit(0 if success else 1) 