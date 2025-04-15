"""
Orchestrator for Action Layer
----------------------------
This module acts as an intermediary between the Reasoning Layer and the Tool Layer,
handling tool invocation, result handling, and user interaction.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Union

from src.agent.reasoning_layer.agent_logic import AgentLogic
from src.agent.tool_layer.ghidra_tools import GhidraTools

logger = logging.getLogger("ollama-ghidra-bridge.agent.action_layer")

class ActionOrchestrator:
    """Orchestrates actions between the Reasoning Layer and Tool Layer."""
    
    def __init__(self, agent_logic: AgentLogic, ghidra_tools: GhidraTools):
        """
        Initialize the action orchestrator.
        
        Args:
            agent_logic: AgentLogic instance for reasoning
            ghidra_tools: GhidraTools instance for tool execution
        """
        self.agent = agent_logic
        self.tools = ghidra_tools
        self.observers: List[Callable[[str, str, str], None]] = []
        logger.info("Initialized Action Orchestrator")
        
    def register_observer(self, observer: Callable[[str, str, str], None]):
        """
        Register an observer for the analysis process.
        
        Args:
            observer: Callback function to receive updates
        """
        self.observers.append(observer)
        
    def notify_observers(self, step_type: str, step_name: str, details: str):
        """
        Notify all registered observers.
        
        Args:
            step_type: Type of step (thought, action, observation, analysis)
            step_name: Name of the step
            details: Details of the step
        """
        for observer in self.observers:
            try:
                observer(step_type, step_name, details)
            except Exception as e:
                logger.error(f"Error notifying observer: {str(e)}")
    
    def _map_tools_to_functions(self) -> Dict[str, Callable]:
        """
        Map tool names to GhidraTools functions.
        
        Returns:
            Dictionary mapping tool names to functions
        """
        # Direct mapping of tool names to GhidraTools methods
        tools_map = {
            "get_function_list": self.tools.get_function_list,
            "get_function_details": self.tools.get_function_details,
            "get_function_details_by_address": self.tools.get_function_details_by_address,
            "get_data_references": self.tools.get_data_references,
            "get_string_at_address": self.tools.get_string_at_address,
            "get_control_flow_graph": self.tools.get_control_flow_graph,
            "get_memory_regions": self.tools.get_memory_regions,
            "search_for_pattern": self.tools.search_for_pattern,
            "get_imports": self.tools.get_imports,
            "get_exports": self.tools.get_exports,
            "rename_function": self.tools.rename_function,
            "add_function_comment": self.tools.add_function_comment,
            "rename_variable": self.tools.rename_variable
        }
        
        return tools_map
    
    def analyze_application(self, task_description: str, system_prompt: Optional[str] = None) -> str:
        """
        Analyze an application using the agent.
        
        Args:
            task_description: Description of the analysis task
            system_prompt: Optional system prompt to guide the LLM's behavior
            
        Returns:
            Analysis report
        """
        logger.info("Starting application analysis")
        
        # Map tool names to functions
        tools_map = self._map_tools_to_functions()
        
        # Update agent with tools and system prompt
        self.agent.available_tools = tools_map
        if system_prompt:
            self.agent.system_prompt = system_prompt
        
        # Start the analysis process with a callback function
        analysis_result = self.agent.analyze_application(
            task_description=task_description,
            callback=self.notify_observers
        )
        
        return analysis_result
    
    def execute_single_action(self, 
                            tool_name: str, 
                            parameters: Dict[str, Any]) -> Union[str, List[str], Dict[str, Any]]:
        """
        Execute a single tool action.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            
        Returns:
            Result of the tool execution
        """
        logger.info(f"Executing single action: {tool_name} with parameters: {parameters}")
        
        # Map tool names to functions
        tools_map = self._map_tools_to_functions()
        
        if tool_name not in tools_map:
            error_msg = f"Tool not found: {tool_name}"
            logger.error(error_msg)
            self.notify_observers("error", "Tool Execution Error", error_msg)
            return error_msg
            
        try:
            # Get the tool function
            tool_function = tools_map[tool_name]
            
            # Execute the tool
            self.notify_observers("action", f"Executing {tool_name}", str(parameters))
            result = tool_function(**parameters)
            self.notify_observers("observation", f"Result of {tool_name}", str(result))
            
            return result
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            self.notify_observers("error", "Tool Execution Error", error_msg)
            return error_msg 