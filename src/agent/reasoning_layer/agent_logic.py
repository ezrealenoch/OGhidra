"""
Agent Logic for Reasoning Layer
------------------------------
This module implements the core decision-making process of the agent
using the Thought-Action-Observation framework.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Callable

from src.agent.reasoning_layer.llm_client import LLMClient
from src.agent.tool_layer.data_transformer import DataTransformer

logger = logging.getLogger("ollama-ghidra-bridge.agent.reasoning_layer")

class AgentMemory:
    """Memory management for the agent to maintain context across iterations."""
    
    def __init__(self, max_observations: int = 10):
        """
        Initialize the agent memory.
        
        Args:
            max_observations: Maximum number of observations to store
        """
        self.observations: List[str] = []
        self.max_observations = max_observations
        self.analysis_results: List[Dict[str, Any]] = []
        
    def add_observation(self, observation: str):
        """
        Add an observation to memory.
        
        Args:
            observation: The observation to add
        """
        self.observations.append(observation)
        if len(self.observations) > self.max_observations:
            # Remove oldest observation
            self.observations.pop(0)
            
    def add_analysis_result(self, result: Dict[str, Any]):
        """
        Add an analysis result to memory.
        
        Args:
            result: The analysis result to add
        """
        self.analysis_results.append(result)
    
    def get_relevant_observations(self, n: Optional[int] = None) -> List[str]:
        """
        Get the most recent observations.
        
        Args:
            n: Number of observations to retrieve (default: all)
            
        Returns:
            List of most recent observations
        """
        if n is None:
            return self.observations
        return self.observations[-n:]
    
    def get_analysis_summary(self) -> str:
        """
        Generate a summary of analysis results.
        
        Returns:
            Summary of analysis results
        """
        if not self.analysis_results:
            return "No analysis results available."
            
        summary = "Analysis Summary:\n\n"
        for i, result in enumerate(self.analysis_results, 1):
            summary += f"Finding {i}: {result.get('finding', 'No description')}\n"
            evidence = result.get('evidence', [])
            if evidence:
                summary += "Evidence:\n"
                for item in evidence:
                    summary += f"- {item}\n"
            summary += "\n"
            
        return summary

class AgentLogic:
    """Core logic for the agentic analysis system."""
    
    def __init__(self, 
                llm_client: LLMClient, 
                available_tools: Dict[str, Callable],
                system_prompt: Optional[str] = None,
                max_iterations: int = 15):
        """
        Initialize the agent logic.
        
        Args:
            llm_client: LLMClient instance for reasoning
            available_tools: Dictionary mapping tool names to tool functions
            system_prompt: Optional system prompt to guide the LLM's behavior
            max_iterations: Maximum number of iterations
        """
        self.llm = llm_client
        self.available_tools = available_tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.memory = AgentMemory()
        logger.info("Initialized Agent Logic with %d available tools", len(available_tools))
        
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Execute a tool with the given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            
        Returns:
            Result of the tool execution
        """
        if tool_name not in self.available_tools:
            logger.error(f"Tool not found: {tool_name}")
            return f"Error: Tool not found: {tool_name}"
            
        try:
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            tool_function = self.available_tools[tool_name]
            result = tool_function(**parameters)
            
            # Transform the result into a suitable format for observation
            if tool_name.startswith("get_") or tool_name.startswith("list_"):
                # For information gathering tools, format the result
                result_str = DataTransformer.format_command_result(tool_name, result)
            else:
                # For modification tools, just use the string result
                result_str = str(result)
                
            return result_str
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            return error_msg
            
    def execute_analysis_iteration(self, 
                                  task_description: str, 
                                  callback: Optional[Callable[[str, str, str], None]] = None) -> Tuple[bool, str]:
        """
        Execute a single iteration of the analysis process.
        
        Args:
            task_description: Description of the analysis task
            callback: Optional callback function for progress updates
            
        Returns:
            Tuple containing:
            - bool: True if analysis should continue, False if complete
            - str: Current observation
        """
        # Get the next action to take
        next_action = self.llm.decide_next_action(
            observations=self.memory.get_relevant_observations(),
            available_tools=list(self.available_tools.keys()),
            task_description=task_description,
            system_prompt=self.system_prompt
        )
        
        # Execute the tool
        tool_name = next_action.get("tool", "")
        parameters = next_action.get("parameters", {})
        reasoning = next_action.get("reasoning", "No reasoning provided")
        
        # If callback is provided, call it with the thought/action
        if callback:
            callback("thought", "Deciding next action", reasoning)
            callback("action", f"Executing tool: {tool_name}", str(parameters))
        
        # Execute the tool and get the observation
        observation = self.execute_tool(tool_name, parameters)
        
        # Add the observation to memory
        self.memory.add_observation(observation)
        
        # If callback is provided, call it with the observation
        if callback:
            callback("observation", "Observed result", observation)
        
        # Determine if we should continue
        continue_analysis = len(self.memory.observations) < self.max_iterations
        
        return continue_analysis, observation
        
    def analyze_application(self, 
                           task_description: str, 
                           callback: Optional[Callable[[str, str, str], None]] = None) -> str:
        """
        Analyze the application behavior through an iterative process.
        
        Args:
            task_description: Description of the analysis task
            callback: Optional callback function for progress updates
            
        Returns:
            Final analysis of the application behavior
        """
        logger.info("Starting application behavior analysis")
        
        iteration = 0
        continue_analysis = True
        
        start_time = time.time()
        
        # Initial observation - list functions as a starting point
        initial_observation = self.execute_tool("get_function_list", {})
        self.memory.add_observation(initial_observation)
        
        if callback:
            callback("observation", "Initial observation", initial_observation)
        
        # Iterative analysis process
        while continue_analysis and iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Starting analysis iteration {iteration}/{self.max_iterations}")
            
            # Execute a single iteration
            continue_analysis, observation = self.execute_analysis_iteration(task_description, callback)
            
            # Check if we've hit the maximum iterations
            if iteration >= self.max_iterations:
                logger.info(f"Reached maximum iterations ({self.max_iterations}), stopping analysis")
                break
                
            # Sleep briefly to avoid overwhelming the system
            time.sleep(0.5)
            
        # Generate final analysis
        final_analysis = self.llm.analyze_application_behavior(
            observations=self.memory.get_relevant_observations(),
            task_description=task_description,
            system_prompt=self.system_prompt
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Completed application behavior analysis in {elapsed_time:.2f} seconds")
        
        if callback:
            callback("analysis", "Final Analysis", final_analysis)
            
        return final_analysis 