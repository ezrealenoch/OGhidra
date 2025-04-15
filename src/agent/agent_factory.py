"""
Agent Factory
-----------
Factory class to simplify creating and initializing the agent.
"""

import logging
import datetime
from typing import Optional, Dict, Any, Callable

from src.config import BridgeConfig
from src.ghidra_client import GhidraMCPClient
from src.ollama_client import OllamaClient

from src.agent.tool_layer import GhidraTools
from src.agent.reasoning_layer import LLMClient, AgentLogic
from src.agent.action_layer import ActionOrchestrator

logger = logging.getLogger("ollama-ghidra-bridge.agent.factory")

class AgentFactory:
    """Factory for creating agent instances."""
    
    @staticmethod
    def create_agent(config: BridgeConfig,
                   ghidra_client: Optional[GhidraMCPClient] = None,
                   ollama_client: Optional[OllamaClient] = None,
                   max_iterations: int = 15) -> ActionOrchestrator:
        """
        Create and initialize an agent.
        
        Args:
            config: BridgeConfig instance
            ghidra_client: Optional GhidraMCPClient instance (if None, a new one will be created)
            ollama_client: Optional OllamaClient instance (if None, a new one will be created)
            max_iterations: Maximum number of iterations for the agent
            
        Returns:
            Initialized ActionOrchestrator instance
        """
        logger.info("Creating agent with max_iterations=%d", max_iterations)
        
        # Create clients if not provided
        if ghidra_client is None:
            ghidra_client = GhidraMCPClient(config.ghidra)
            logger.info("Created new GhidraMCPClient")
            
        if ollama_client is None:
            ollama_client = OllamaClient(config.ollama)
            logger.info("Created new OllamaClient")
            
        # Create the tool layer
        ghidra_tools = GhidraTools(ghidra_client)
        
        # Create the reasoning layer
        llm_client = LLMClient(ollama_client)
        
        # Create agent logic
        agent_logic = AgentLogic(
            llm_client=llm_client,
            available_tools={},  # Will be populated by orchestrator
            system_prompt=None,  # Will be set below after orchestrator creation
            max_iterations=max_iterations
        )
        
        # Create action orchestrator
        orchestrator = ActionOrchestrator(
            agent_logic=agent_logic,
            ghidra_tools=ghidra_tools
        )
        
        # Define system prompt for behavioral analysis
        # Get the available tools description from the orchestrator
        available_tools_description = orchestrator.get_available_tools_description()
        
        system_prompt = f"""You are an expert reverse engineer analyzing application behavior using Ghidra.
Your task is to analyze the behavior of a binary application using the available Ghidra analysis tools.

{available_tools_description}

IMPORTANT: You can ONLY use the tools listed above. Do not attempt to use any other tools.
If you try a tool that isn't available, you'll receive suggestions for alternative tools.

When examining functions and data, look for:
1. Main program flow and key functionality
2. Interesting API calls or operations
3. Potential security issues or vulnerabilities
4. Data access patterns
5. Communication with external systems

Analysis Workflow Guidelines:
1. Start by exploring basic program structure (functions, imports, exports)
2. Focus on key functions with meaningful names or important imports
3. Use disassemble_function or decompile_function to analyze interesting functions
4. Examine memory regions and data patterns
5. Draw conclusions about the program's overall behavior

Provide clear reasoning for your observations and decisions. 
When making conclusions, cite specific evidence from the binary.
"""
        
        # Set the system prompt in the agent
        agent_logic.system_prompt = system_prompt
        
        logger.info("Successfully created agent")
        return orchestrator
    
    @staticmethod
    def create_progress_observer(progress_callback: Callable[[str, Dict[str, Any]], None]) -> Callable[[str, str, str], None]:
        """
        Create an observer function for tracking agent progress.
        
        Args:
            progress_callback: Callback function that takes an event_type and a data dictionary
            
        Returns:
            Observer function compatible with the agent's notification system
        """
        def observer(step_type: str, step_name: str, details: str):
            # Format the data as a dictionary
            data = {
                "step_type": step_type,
                "step_name": step_name,
                "details": details,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Call the progress callback
            progress_callback("agent_progress", data)
            
        return observer 