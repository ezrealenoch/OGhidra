"""
LLM Client for Reasoning Layer
-----------------------------
This module handles interaction with the local LLM model.
"""

import logging
from typing import Dict, Any, List, Optional

from src.ollama_client import OllamaClient

logger = logging.getLogger("ollama-ghidra-bridge.agent.reasoning_layer")

class LLMClient:
    """Client for interacting with a locally hosted LLM."""
    
    def __init__(self, ollama_client: OllamaClient):
        """
        Initialize the LLM client.
        
        Args:
            ollama_client: OllamaClient instance for LLM interaction
        """
        self.ollama = ollama_client
        logger.info("Initialized LLM client")
    
    def generate_thought(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a thought or reasoning based on the given prompt.
        
        Args:
            prompt: The prompt for the LLM
            system_prompt: Optional system prompt to guide the model's behavior
            
        Returns:
            The LLM's response as a string
        """
        logger.info("Generating thought with LLM")
        return self.ollama.generate(prompt, system_prompt)
    
    def decide_next_action(self, 
                          observations: List[str], 
                          available_tools: List[str],
                          task_description: str,
                          system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Decide the next action to take based on observations and available tools.
        
        Args:
            observations: List of observations from previous actions
            available_tools: List of available tools
            task_description: Description of the current task
            system_prompt: Optional system prompt to guide the model's behavior
            
        Returns:
            Dictionary containing the next action details:
            - tool: Name of the tool to use
            - parameters: Parameters for the tool
            - reasoning: Reasoning behind this action
        """
        # Construct a prompt for decision-making
        tools_str = "\n".join([f"- {tool}" for tool in available_tools])
        observations_str = "\n\n".join(observations)
        
        prompt = f"""# Task
{task_description}

# Available Tools
{tools_str}

# Observations
{observations_str}

# Thinking
Based on the observations so far and the current task, what is the most appropriate next action to take?
Think through this step by step. Consider what information you already have and what information you still need.

# Next Action
Given your reasoning, what tool would you like to use next from the available tools list? 
You MUST pick a tool from the available tools list above.

Provide your response in the following format:
```json
{{
  "tool": "tool_name",
  "parameters": {{"param1": "value1", "param2": "value2"}},
  "reasoning": "Detailed explanation of why this action is appropriate"
}}
```

REMEMBER: Only choose tools from the available list. Provide a proper JSON format with string values properly quoted.
"""
        
        # Generate a response
        response = self.ollama.generate(prompt, system_prompt)
        
        # Extract the JSON from the response
        import json
        import re
        
        # Try to find JSON pattern in the response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
            try:
                action_data = json.loads(json_str)
                
                # Validate the action data
                if "tool" not in action_data:
                    raise ValueError("Missing 'tool' field in action data")
                if action_data["tool"] not in available_tools:
                    logger.warning(f"Tool '{action_data['tool']}' not in available tools, using default")
                    action_data["tool"] = available_tools[0]
                if "parameters" not in action_data:
                    action_data["parameters"] = {}
                if "reasoning" not in action_data:
                    action_data["reasoning"] = "No reasoning provided"
                
                return action_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from response: {json_str}")
                logger.error(f"JSON error: {str(e)}")
                # Try more aggressive parsing
                try:
                    # Try to extract tool name
                    tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', json_str)
                    reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', json_str)
                    
                    if tool_match and tool_match.group(1) in available_tools:
                        tool = tool_match.group(1)
                        reasoning = reasoning_match.group(1) if reasoning_match else "Extracted from malformed JSON"
                        
                        logger.info(f"Extracted tool '{tool}' from malformed JSON")
                        
                        return {
                            "tool": tool,
                            "parameters": {},
                            "reasoning": reasoning
                        }
                except Exception as e2:
                    logger.error(f"Failed to extract tool from malformed JSON: {str(e2)}")
                
                # Return a default action if parsing fails
                return {
                    "tool": available_tools[0],
                    "parameters": {},
                    "reasoning": f"Default action due to error in parsing LLM response. Error: {str(e)}"
                }
        else:
            # If no JSON pattern is found, try to infer the action from the response
            logger.warning("No JSON found in response, attempting to infer action")
            
            # Try to find mentions of tools in the text
            for tool in available_tools:
                if tool in response:
                    logger.info(f"Inferred tool '{tool}' from response text")
                    return {
                        "tool": tool,
                        "parameters": {},
                        "reasoning": "Inferred action from non-structured response"
                    }
            
            # Default to first available tool if we can't determine a more appropriate action
            return {
                "tool": available_tools[0],
                "parameters": {},
                "reasoning": "Using default tool since no tool could be inferred from response"
            }
    
    def analyze_application_behavior(self, 
                                    observations: List[str],
                                    task_description: str,
                                    system_prompt: Optional[str] = None) -> str:
        """
        Analyze the application behavior based on observations.
        
        Args:
            observations: List of observations from previous actions
            task_description: Description of the current task
            system_prompt: Optional system prompt to guide the model's behavior
            
        Returns:
            Analysis of the application behavior
        """
        # Construct a prompt for analysis
        observations_str = "\n\n".join(observations)
        
        prompt = f"""# Task
{task_description}

# Observations
{observations_str}

# Analysis
Based on the observations above, analyze the behavior of the application.
Consider:
1. What is the main purpose of the application?
2. What are the key functionalities?
3. Are there any potentially suspicious or malicious behaviors?
4. What is the overall architecture and flow of the application?

Provide a detailed analysis of the application's behavior, citing specific evidence from the observations.
"""
        
        # Generate a response
        logger.info("Generating application behavior analysis with LLM")
        return self.ollama.generate(prompt, system_prompt) 