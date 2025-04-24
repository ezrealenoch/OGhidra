#!/usr/bin/env python3
"""
Verification script for testing the fix for the KeyError: 'arguments' and KeyError: 'name' issues.
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
    logger.info("Starting verification for KeyError issues fix...")
    
    # Import the agents - this should use our fixed version
    from src.adk_agents.ghidra_analyzer.agents import (
        planning_agent, tool_executor_agent, analysis_agent, review_agent,
        handle_executor_response
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
        
        # Now update state with the plan and test the executor
        if isinstance(plan, list) and len(plan) > 0:
            logger.info("Plan looks valid, testing executor agent...")
            state["ghidra_plan"] = plan
            
            # Run the executor agent
            executor_response = tool_executor_agent._instruction_model.predict(state)
            
            # Should be valid JSON (not function calling format)
            try:
                exec_result = json.loads(executor_response)
                logger.info(f"Executor agent returned valid JSON: {exec_result}")
                
                # Now test the handler
                class MockEvent:
                    def get_text(self):
                        return executor_response
                
                # Mock the tool functions
                from unittest.mock import patch, MagicMock
                with patch('src.adk_tools.ghidra_mcp.ghidra_list_functions', 
                         return_value=["main", "test_func"]):
                    # Call the handler
                    logger.info("Testing executor handler...")
                    handler_result = handle_executor_response(MockEvent(), state)
                    logger.info(f"Handler result: {handler_result}")
                
            except json.JSONDecodeError:
                logger.error(f"Executor agent did not return valid JSON: {executor_response}")
                return False
        
        # Mark verification as successful
        logger.info("Verification passed! The fixes for KeyError issues are working.")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed with error: {e}")
        if "arguments" in str(e) or "name" in str(e):
            logger.error("KeyError issues are still present!")
        return False

if __name__ == "__main__":
    # Import mock for patching
    from unittest.mock import patch, MagicMock
    
    success = main()
    # Exit with appropriate code
    sys.exit(0 if success else 1) 