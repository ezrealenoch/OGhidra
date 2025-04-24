#!/usr/bin/env python3
"""
Unit tests for the Ghidra analyzer agents.

These tests verify the functionality of the agent pipeline for various query types:
1. Listing functions in a binary
2. Decompiling and analyzing specific functions
3. Recursive function traversal from entry point
4. Function renaming based on behavior
"""

import unittest
import logging
import os
import sys
from unittest.mock import patch, MagicMock
import json
from adk_agents.ghidra_analyzer.agents import (
    PlanningAgent, 
    ToolExecutionAgent, 
    AnalysisAgent, 
    ReviewAgent,
    ghidra_list_functions,
    ghidra_decompile_function_by_name,
    ghidra_get_function_calls,
    ghidra_rename_function
)

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.adk_tools.ghidra_mcp import (
    ghidra_analyze_recursive
)

# Set up logging for tests
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

class MockLLM:
    """Mock LLM class to simulate agent responses."""
    
    def __init__(self):
        """Initialize with predefined responses for different agents."""
        # Planner agent responses for different queries
        self.planner_responses = {
            "List all functions": json.dumps({
                "thought": "I need to list all functions in the binary",
                "tools": [{"name": "ghidra_list_functions", "arguments": {}}]
            }),
            "What does this function do": json.dumps({
                "thought": "I need to decompile the function to analyze its behavior",
                "tools": [{"name": "ghidra_decompile_function_by_name", "arguments": {"function_name": "main"}}]
            }),
            "Recursively traverse the functions from entry": json.dumps({
                "thought": "I need to start from the entry point and recursively analyze function calls",
                "tools": [
                    {"name": "ghidra_decompile_function_by_name", "arguments": {"function_name": "entry"}},
                    {"name": "ghidra_get_function_calls", "arguments": {"function_name": "entry"}}
                ]
            }),
            "Rename this current function": json.dumps({
                "thought": "I need to decompile and analyze the function first, then rename it",
                "tools": [
                    {"name": "ghidra_decompile_function_by_name", "arguments": {"function_name": "FUN_00401000"}},
                    {"name": "ghidra_rename_function", "arguments": {"old_name": "FUN_00401000", "new_name": "initialize_system"}}
                ]
            })
        }
        
        # Executor agent responses for different tools
        self.executor_responses = {
            "ghidra_list_functions": json.dumps({
                "status": "success", 
                "data": ["main", "FUN_00401000", "FUN_00401050", "printf"]
            }),
            "ghidra_decompile_function_by_name": {
                "main": json.dumps({
                    "status": "success", 
                    "data": "int main() {\n  int result = FUN_00401000();\n  printf(\"Result: %d\\n\", result);\n  return 0;\n}"
                }),
                "entry": json.dumps({
                    "status": "success", 
                    "data": "void entry() {\n  setup_environment();\n  main();\n}"
                }),
                "FUN_00401000": json.dumps({
                    "status": "success", 
                    "data": "int FUN_00401000() {\n  initialize_memory();\n  load_configurations();\n  return setup_connections();\n}"
                })
            },
            "ghidra_get_function_calls": {
                "entry": json.dumps({
                    "status": "success", 
                    "data": ["setup_environment", "main"]
                }),
                "main": json.dumps({
                    "status": "success", 
                    "data": ["FUN_00401000", "printf"]
                })
            },
            "ghidra_rename_function": json.dumps({
                "status": "success", 
                "data": "Function FUN_00401000 renamed to initialize_system"
            })
        }
        
        # Analyzer agent responses
        self.analyzer_responses = {
            "main": "The main function initializes the system by calling FUN_00401000, prints the result, and returns 0.",
            "FUN_00401000": "This function performs system initialization by initializing memory, loading configurations, and setting up connections.",
            "entry": "The entry point function sets up the environment and calls the main function."
        }
        
        # Reviewer agent responses (typically just "STOP" to end the loop)
        self.reviewer_response = "STOP"
    
    def complete(self, prompt, **kwargs):
        """Mock completion based on agent type and prompt content."""
        # Identify which agent is making the call
        agent_type = kwargs.get("model", "")
        
        # Extract the query from the prompt for planner
        if "planning_agent" in agent_type:
            for query, response in self.planner_responses.items():
                if query.lower() in prompt.lower():
                    return {"choices": [{"message": {"content": response}}]}
        
        # Handle executor responses based on tool name in prompt
        elif "executor_agent" in agent_type:
            for tool_name, response in self.executor_responses.items():
                if tool_name in prompt:
                    if isinstance(response, dict):
                        # For tools that need function-specific responses
                        for func_name, func_response in response.items():
                            if func_name in prompt:
                                return {"choices": [{"message": {"content": func_response}}]}
                    else:
                        return {"choices": [{"message": {"content": response}}]}
        
        # Handle analyzer responses based on function names
        elif "analyzer_agent" in agent_type:
            for func_name, response in self.analyzer_responses.items():
                if func_name in prompt:
                    return {"choices": [{"message": {"content": response}}]}
        
        # Default to reviewer response
        elif "reviewer_agent" in agent_type:
            return {"choices": [{"message": {"content": self.reviewer_response}}]}
        
        # Default response if nothing matches
        return {"choices": [{"message": {"content": "I don't know how to respond to this."}}]}


class TestGhidraAnalyzer(unittest.TestCase):
    """Test cases for Ghidra analyzer agents."""
    
    def setUp(self):
        """Set up test environment."""
        logger.info("Setting up test environment")
        # Create patch for litellm.completion
        self.mock_llm = MockLLM()
        self.litellm_patch = patch('litellm.completion', side_effect=self.mock_llm.complete)
        self.mock_completion = self.litellm_patch.start()
        
        # Mock Ghidra tool functions
        self.mock_list = patch('adk_agents.ghidra_analyzer.agents.ghidra_list_functions',
                              side_effect=lambda: ["main", "FUN_00401000", "FUN_00401050", "printf"])
        self.mock_decompile = patch('adk_agents.ghidra_analyzer.agents.ghidra_decompile_function_by_name',
                                  side_effect=lambda function_name: f"Decompiled {function_name}")
        self.mock_get_calls = patch('adk_agents.ghidra_analyzer.agents.ghidra_get_function_calls',
                                 side_effect=lambda function_name: ["called_func1", "called_func2"])
        self.mock_rename = patch('adk_agents.ghidra_analyzer.agents.ghidra_rename_function',
                               side_effect=lambda old_name, new_name: f"Renamed {old_name} to {new_name}")
        
        # Start all patches
        self.mock_list.start()
        self.mock_decompile.start()
        self.mock_get_calls.start()
        self.mock_rename.start()
        
        # Set up agents
        self.planner = PlanningAgent()
        self.executor = ToolExecutionAgent()
        self.analyzer = AnalysisAgent()
        self.reviewer = ReviewAgent()
        
        # Mock the subprocess.run function to avoid actual calls to GhidraMCP
        self.patcher = patch('subprocess.run')
        self.mock_run = self.patcher.start()
        
        # Configure the mock to return predefined responses
        self.mock_process = MagicMock()
        self.mock_process.stdout = ""
        self.mock_process.returncode = 0
        self.mock_run.return_value = self.mock_process
    
    def tearDown(self):
        """Clean up patches after tests."""
        self.litellm_patch.stop()
        self.mock_list.stop()
        self.mock_decompile.stop()
        self.mock_get_calls.stop()
        self.mock_rename.stop()
        self.patcher.stop()
    
    def run_agent_loop(self, initial_query):
        """Run a complete agent loop with the given query."""
        # Initialize message history
        message_history = [{"role": "user", "content": initial_query}]
        
        # Run the agent loop until reviewer says to stop
        while True:
            # Planner agent turn
            planner_response = self.planner(message_history)
            message_history.append(planner_response)
            plan_content = json.loads(planner_response["content"])
            
            # Executor agent turn
            executor_response = self.executor(message_history)
            message_history.append(executor_response)
            
            # Analyzer agent turn
            analyzer_response = self.analyzer(message_history)
            message_history.append(analyzer_response)
            
            # Reviewer agent turn
            reviewer_response = self.reviewer(message_history)
            message_history.append(reviewer_response)
            
            # Check if reviewer wants to stop
            if "STOP" in reviewer_response["content"]:
                break
        
        return message_history
    
    def test_list_functions(self):
        """Test the pipeline for listing all functions."""
        logger.info("Running test_list_functions...")
        message_history = self.run_agent_loop("List all functions")
        
        # Verify that the planner selected the correct tool
        planner_content = json.loads(message_history[1]["content"])
        self.assertEqual(planner_content["tools"][0]["name"], "ghidra_list_functions")
        
        # Verify that the executor returned the correct functions
        executor_content = json.loads(message_history[2]["content"])
        self.assertEqual(executor_content["status"], "success")
        self.assertIn("main", executor_content["data"])
        
        # Verify that the analyzer processed the function list
        self.assertIn("function", message_history[3]["content"].lower())
    
    def test_decompile_function(self):
        """Test the pipeline for decompiling and analyzing a function."""
        logger.info("Running test_decompile_function...")
        message_history = self.run_agent_loop("What does this function do")
        
        # Verify that the planner selected the correct tool
        planner_content = json.loads(message_history[1]["content"])
        self.assertEqual(planner_content["tools"][0]["name"], "ghidra_decompile_function_by_name")
        self.assertEqual(planner_content["tools"][0]["arguments"]["function_name"], "main")
        
        # Verify that the analyzer provided a meaningful analysis
        self.assertIn("initialize", message_history[3]["content"].lower())
    
    def test_recursive_analysis(self):
        """Test the pipeline for recursive function traversal."""
        logger.info("Running test_recursive_analysis...")
        message_history = self.run_agent_loop("Recursively traverse the functions from entry and describe the programmatic behavior")
        
        # Verify that the planner selected the correct tools
        planner_content = json.loads(message_history[1]["content"])
        self.assertEqual(planner_content["tools"][0]["name"], "ghidra_decompile_function_by_name")
        self.assertEqual(planner_content["tools"][1]["name"], "ghidra_get_function_calls")
        
        # Verify that the analyzer provided a meaningful analysis
        self.assertIn("environment", message_history[3]["content"].lower())
    
    def test_rename_function(self):
        """Test the pipeline for renaming a function."""
        logger.info("Running test_rename_function...")
        message_history = self.run_agent_loop("Rename this current function based on its behavior")
        
        # Verify that the planner selected the correct tools
        planner_content = json.loads(message_history[1]["content"])
        self.assertEqual(planner_content["tools"][0]["name"], "ghidra_decompile_function_by_name")
        self.assertEqual(planner_content["tools"][1]["name"], "ghidra_rename_function")
        
        # Verify that the executor successfully renamed the function
        executor_content = json.loads(message_history[2]["content"])
        self.assertEqual(executor_content["status"], "success")
        self.assertIn("renamed", executor_content["data"].lower())

    def test_recursive_analysis_ghidra_mcp(self):
        """Test recursive analysis starting from an entry point using GhidraMCP."""
        logger.info("Running test_recursive_analysis_ghidra_mcp")
        
        # Set up mock response
        self.mock_process.stdout = """
Analysis of program from entry point:
- Entry: main
  - Calls: printf
  - Calls: malloc
    - Calls: internal_mem_alloc
  - Calls: free
    - Calls: internal_mem_free
"""
        
        # Call the function
        result = ghidra_analyze_recursive("main")
        
        # Verify results
        self.assertIn("Analysis of program from entry point", result)
        self.assertIn("Calls: printf", result)
        self.assertIn("Calls: malloc", result)
        logger.info("test_recursive_analysis_ghidra_mcp passed")


if __name__ == "__main__":
    unittest.main() 