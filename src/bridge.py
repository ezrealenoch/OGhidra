#!/usr/bin/env python3
"""
Ollama-GhidraMCP Bridge
-----------------------
This application acts as a bridge between a locally hosted Ollama AI model
and GhidraMCP, enabling AI-assisted reverse engineering tasks within Ghidra.
"""

import argparse
import json
import logging
import sys
import os
import re  # Added for pattern matching in enhanced error feedback
from typing import Dict, Any, List, Optional, Tuple, Union

from src.config import BridgeConfig
from src.ollama_client import OllamaClient
from src.ghidra_client import GhidraMCPClient
from src.command_parser import CommandParser

# Configure logging
def setup_logging(config):
    """Set up logging configuration."""
    handlers = []
    
    if config.logging.console_logging:
        handlers.append(logging.StreamHandler(sys.stdout))
        
    if config.logging.file_logging:
        handlers.append(logging.FileHandler(config.logging.log_file))
        
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format,
        handlers=handlers
    )
    
    return logging.getLogger("ollama-ghidra-bridge")

class Bridge:
    """Main bridge class that connects Ollama with GhidraMCP."""
    
    def __init__(self, config: BridgeConfig, include_capabilities: bool = False, max_agent_steps: int = 5, max_review_rounds: int = 3):
        """
        Initialize the bridge.
        
        Args:
            config: BridgeConfig object with configuration settings
            include_capabilities: Flag to include capabilities in prompt
            max_agent_steps: Maximum number of steps for agentic execution loop
            max_review_rounds: Maximum number of review rounds after tool execution
        """
        self.config = config
        self.logger = setup_logging(config)
        self.ollama = OllamaClient(config.ollama)
        self.ghidra = GhidraMCPClient(config.ghidra)
        self.context = []  # Store conversation context
        self.include_capabilities = include_capabilities
        self.capabilities_text = self._load_capabilities_text()
        self.logger.info(f"Bridge initialized with Ollama at {config.ollama.base_url} and GhidraMCP at {config.ghidra.base_url}")
        self.max_agent_steps = max_agent_steps  # Maximum number of steps for agentic execution loop
        self.max_review_rounds = max_review_rounds  # Maximum number of review rounds after tool execution
        if self.include_capabilities and self.capabilities_text:
            self.logger.info("Capabilities context will be included in prompts.")
        elif self.include_capabilities:
            self.logger.warning("`--include-capabilities` flag set, but `ai_ghidra_capabilities.txt` not found or empty.")
    
    def _load_capabilities_text(self) -> Optional[str]:
        """Load the capabilities text from the file if the flag is set."""
        if not self.include_capabilities:
            return None
            
        capabilities_file = "ai_ghidra_capabilities.txt"
        try:
            # Assuming the script is run from the project root
            file_path = os.path.join(os.path.dirname(__file__), '..', capabilities_file) 
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # Try reading from the current working directory as a fallback
                if os.path.exists(capabilities_file):
                    with open(capabilities_file, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    self.logger.warning(f"Capabilities file '{capabilities_file}' not found.")
                    return None
        except Exception as e:
            self.logger.error(f"Error reading capabilities file '{capabilities_file}': {str(e)}")
            return None

    def _build_structured_prompt(self) -> str:
        """
        Build a structured prompt with clear sections for capabilities, history, and current task.
        
        Returns:
            A structured prompt string with labeled sections
        """
        # Capabilities section
        capabilities_section = ""
        if self.include_capabilities and self.capabilities_text:
            capabilities_section = (
                f"## Available Tools:\n"
                f"You have access to the following Ghidra interaction tools. "
                f"Use the `EXECUTE: tool_name(param1=value1, ...)` format to call them.\n"
                f"```text\n{self.capabilities_text}\n```\n---\n\n"
            )
        
        # Conversation history section
        history_items = []
        for item in self.context[-self.config.context_limit:]:
            prefix = "User: " if item["role"] == "user" else \
                    "Assistant: " if item["role"] == "assistant" else \
                    "Tool Call: " if item["role"] == "tool_call" else \
                    "Tool Result: " if item["role"] == "tool_result" else \
                    "AI Review: " if item["role"] == "review" else \
                    f"{item['role'].capitalize()}: "
            history_items.append(f"{prefix}{item['content']}")
        
        history_section = "## Conversation History:\n" + "\n".join(history_items) + "\n---\n\n"
        
        # Instructions section - always included
        instructions_section = (
            "## Instructions:\n"
            "1. Analyze the user request carefully based on available context\n"
            "2. Use tools by writing `EXECUTE: tool_name(param1=value1, ...)` for each tool call\n"
            "3. IMPORTANT FOR RENAME OPERATIONS: When using rename_function_by_address, "
            "the function_address parameter must be the numerical address (e.g., '1800011a8'), not the function name (e.g., 'FUN_1800011a8')\n"
            "4. Provide analysis along with your tool calls\n"
            "5. Your response should be clear and concise\n"
            "6. When you have completed your analysis and are ready to provide a final answer, include \"FINAL RESPONSE:\" followed by your complete answer\n"
            "---\n\n"
        )
        
        # Create the full prompt
        full_prompt = capabilities_section + history_section + instructions_section
        
        # Add final response request only if last message was from user
        if self.context and self.context[-1]["role"] == "user":
            full_prompt += "## Your Response:\n"
        elif self.context and self.context[-1]["role"] == "review":
            full_prompt += "## Continue Your Analysis:\nBased on the review feedback, continue your analysis or finalize your response.\n"
            
        return full_prompt
    
    def process_query(self, query: str) -> str:
        """
        Process a natural language query through the AI and execute commands on GhidraMCP,
        with optional multi-step agentic reasoning.
        
        Args:
            query: The user's query
            
        Returns:
            The processed response with command results
        """
        # Add the query to context
        self.context.append({"role": "user", "content": query})
        
        # Initialize the final response variable
        final_response = ""
        
        # Primary agentic execution loop - allows multiple steps of reasoning with tools
        for step in range(self.max_agent_steps):
            # Build the structured prompt
            prompt = self._build_structured_prompt()
            
            # Send to Ollama
            self.logger.info(f"Step {step+1}/{self.max_agent_steps}: Sending query to Ollama")
            
            try:
                # Get AI response
                ai_response = self.ollama.generate(prompt, self.config.ollama.default_system_prompt)
                self.logger.info(f"Received response from Ollama: {ai_response[:100]}...")
                
                # Parse commands from the response
                commands = CommandParser.extract_commands(ai_response)
                
                # Clean the response text (remove EXECUTE blocks)
                clean_response = self._remove_commands(ai_response)
                
                # Add the clean response to context
                if clean_response.strip():
                    self.context.append({"role": "assistant", "content": clean_response.strip()})
                    final_response = clean_response.strip()
                
                # If no commands found, we're done with the tool execution phase
                if not commands:
                    self.logger.info("No commands found in AI response, ending tool execution loop")
                    break
                
                # Execute each command and add to context
                all_results = []
                for cmd_name, cmd_params in commands:
                    # Add tool call to context
                    params_str = ", ".join([f"{k}=\"{v}\"" for k, v in cmd_params.items()])
                    tool_call = f"EXECUTE: {cmd_name}({params_str})"
                    self.context.append({"role": "tool_call", "content": tool_call})
                    
                    # Execute the command
                    result = self._execute_single_command(cmd_name, cmd_params)
                    all_results.append((tool_call, result))
                    
                    # Add result to context
                    self.context.append({"role": "tool_result", "content": result})
                
                # Update final response with results
                final_response = clean_response + "\n\n" + "\n".join([result for _, result in all_results])
                
                # Check if any command failed - if so, let the AI try again in the next step
                any_errors = any(["ERROR" in result or "Failed" in result for _, result in all_results])
                if not any_errors:
                    # If all commands succeeded, we can break the loop
                    self.logger.info("All commands executed successfully, ending tool execution loop")
                    break
                
            except Exception as e:
                error_msg = f"Error in agent step {step+1}: {str(e)}"
                self.logger.error(error_msg)
                final_response = f"Sorry, I encountered an error: {str(e)}"
                break
        
        # Secondary review and reasoning loop - evaluates completeness of response
        self.logger.info("Starting review and reasoning phase")
        review_step = 0
        has_final_response = False
        
        while review_step < self.max_review_rounds and not has_final_response:
            # Check if current final_response already contains "FINAL RESPONSE"
            if "FINAL RESPONSE:" in final_response:
                has_final_response = True
                self.logger.info("Found 'FINAL RESPONSE' marker, ending review loop")
                # Extract the part after "FINAL RESPONSE:"
                final_parts = final_response.split("FINAL RESPONSE:", 1)
                if len(final_parts) > 1:
                    final_response = final_parts[1].strip()
                break
                
            # Add a review prompt to encourage finalizing the response
            review_prompt = (
                f"Review your analysis so far. Have you completed the task? "
                f"If not, what additional information or analysis is needed? "
                f"If yes, provide a complete and comprehensive final answer prefixed with 'FINAL RESPONSE:'"
            )
            self.context.append({"role": "review", "content": review_prompt})
            
            # Build a new prompt with the review context
            prompt = self._build_structured_prompt()
            
            # Send to Ollama for review
            self.logger.info(f"Review step {review_step+1}/{self.max_review_rounds}: Asking AI to review response")
            
            try:
                # Get AI's review response
                ai_review_response = self.ollama.generate(prompt, self.config.ollama.default_system_prompt)
                self.logger.info(f"Received review response: {ai_review_response[:100]}...")
                
                # Clean the response and update
                clean_review = self._remove_commands(ai_review_response)
                if clean_review.strip():
                    self.context.append({"role": "assistant", "content": clean_review.strip()})
                    final_response = clean_review.strip()
                    
                    # Check if this response has the final marker
                    if "FINAL RESPONSE:" in clean_review:
                        has_final_response = True
                        self.logger.info("Found 'FINAL RESPONSE' marker, ending review loop")
                        # Extract the part after "FINAL RESPONSE:"
                        final_parts = clean_review.split("FINAL RESPONSE:", 1)
                        if len(final_parts) > 1:
                            final_response = final_parts[1].strip()
                        break
                
                # Process any additional commands if present
                commands = CommandParser.extract_commands(ai_review_response)
                if commands:
                    self.logger.info(f"Found {len(commands)} additional commands in review response")
                    # Execute each command and add to context (similar to primary loop)
                    for cmd_name, cmd_params in commands:
                        # Add tool call to context
                        params_str = ", ".join([f"{k}=\"{v}\"" for k, v in cmd_params.items()])
                        tool_call = f"EXECUTE: {cmd_name}({params_str})"
                        self.context.append({"role": "tool_call", "content": tool_call})
                        
                        # Execute the command
                        result = self._execute_single_command(cmd_name, cmd_params)
                        
                        # Add result to context
                        self.context.append({"role": "tool_result", "content": result})
                        
                        # Don't override final_response here, just add results to context
            
            except Exception as e:
                error_msg = f"Error in review step {review_step+1}: {str(e)}"
                self.logger.error(error_msg)
                if not final_response:  # Only set if we don't already have a response
                    final_response = f"Sorry, I encountered an error during review: {str(e)}"
                break
                
            review_step += 1
                
        # If we exited the loop without finding a final response marker, just use what we have
        if not has_final_response:
            self.logger.info(f"Reached maximum review rounds ({self.max_review_rounds}) without final response marker")
            
        return final_response
    
    def _remove_commands(self, text: str) -> str:
        """
        Remove EXECUTE command blocks from text to get the clean response.
        
        Args:
            text: The text containing EXECUTE blocks
            
        Returns:
            Clean text with EXECUTE blocks removed
        """
        return CommandParser.remove_commands(text)
    
    def _execute_single_command(self, command_name: str, params: Dict[str, Any]) -> str:
        """
        Execute a single GhidraMCP command with enhanced error handling.
        
        Args:
            command_name: Name of the GhidraMCP command
            params: Command parameters
            
        Returns:
            Result or error string
        """
        try:
            # Check if the command is available in the GhidraMCP client
            if hasattr(self.ghidra, command_name):
                self.logger.info(f"Executing GhidraMCP command: {command_name} with params: {params}")
                
                # Call the method on the GhidraMCP client
                cmd_method = getattr(self.ghidra, command_name)
                cmd_result = cmd_method(**params)
                
                # Check if there was an error
                if isinstance(cmd_result, dict) and "error" in cmd_result:
                    error_msg = CommandParser.get_enhanced_error_message(
                        command_name, params, cmd_result.get("error", "Unknown error")
                    )
                    self.logger.error(error_msg)
                    return error_msg
                elif isinstance(cmd_result, str) and ("Failed" in cmd_result or "Error" in cmd_result):
                    error_msg = CommandParser.get_enhanced_error_message(
                        command_name, params, cmd_result
                    )
                    self.logger.error(error_msg)
                    return error_msg
                else:
                    # Format the command result
                    if isinstance(cmd_result, (list, dict)):
                        formatted_result = f"RESULT: {json.dumps(cmd_result, indent=2)}"
                    else:
                        formatted_result = f"RESULT: {cmd_result}"
                    return formatted_result
            else:
                error_msg = f"ERROR: Unknown command '{command_name}'"
                self.logger.error(error_msg)
                return error_msg
        except Exception as e:
            error_msg = CommandParser.get_enhanced_error_message(
                command_name, params, str(e)
            )
            self.logger.error(error_msg)
            return error_msg
    
    def _parse_and_execute_commands(self, response: str) -> str:
        """
        Parse the AI response to identify and execute GhidraMCP commands.
        
        Args:
            response: The AI's response text
            
        Returns:
            The processed response with command results
        """
        # Extract commands using the CommandParser
        commands = CommandParser.extract_commands(response)
        
        if not commands:
            # No commands to execute, return the response as is
            return response
            
        # Process each command
        for command_name, params in commands:
            try:
                # Check if the command is available in the GhidraMCP client
                if hasattr(self.ghidra, command_name):
                    self.logger.info(f"Executing GhidraMCP command: {command_name} with params: {params}")
                    
                    # Call the method on the GhidraMCP client
                    cmd_method = getattr(self.ghidra, command_name)
                    cmd_result = cmd_method(**params)
                    
                    # Check if there was an error
                    if isinstance(cmd_result, dict) and "error" in cmd_result:
                        error_msg = f"ERROR: {cmd_result.get('error')}"
                        self.logger.error(error_msg)
                        # Replace the command with the error message
                        command_str = f"EXECUTE: {command_name}({', '.join([f'{k}=\"{v}\"' for k, v in params.items()])})"
                        response = response.replace(command_str, error_msg)
                    else:
                        # Format the command result
                        formatted_result = f"RESULT: {json.dumps(cmd_result, indent=2)}"
                        
                        # Replace the command with the result in the response
                        command_str = f"EXECUTE: {command_name}({', '.join([f'{k}=\"{v}\"' for k, v in params.items()])})"
                        response = response.replace(command_str, formatted_result)
                else:
                    error_msg = f"ERROR: Unknown command '{command_name}'"
                    self.logger.error(error_msg)
                    # Replace the command with the error message
                    command_str = f"EXECUTE: {command_name}({', '.join([f'{k}=\"{v}\"' for k, v in params.items()])})"
                    response = response.replace(command_str, error_msg)
            except Exception as e:
                error_msg = f"ERROR: Failed to execute '{command_name}': {str(e)}"
                self.logger.error(error_msg)
                # Replace the command with the error message
                command_str = f"EXECUTE: {command_name}({', '.join([f'{k}=\"{v}\"' for k, v in params.items()])})"
                response = response.replace(command_str, error_msg)
        
        return response
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check the health of both Ollama and GhidraMCP services.
        
        Returns:
            Dict with health status of each service
        """
        return {
            "ollama": self.ollama.health_check(),
            "ghidra": self.ghidra.health_check()
        }

def main():
    """Main entry point for the bridge application."""
    parser = argparse.ArgumentParser(description="Ollama-GhidraMCP Bridge")
    parser.add_argument("--ollama-url", help="Ollama server URL")
    parser.add_argument("--ghidra-url", help="GhidraMCP server URL")
    parser.add_argument("--model", help="Ollama model to use")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--health-check", action="store_true", help="Check health of services and exit")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no GhidraMCP server needed)")
    parser.add_argument("--include-capabilities", action="store_true", 
                        help="Include capabilities context from ai_ghidra_capabilities.txt in prompts")
    parser.add_argument("--max-steps", type=int, default=5, 
                        help="Maximum number of steps for agentic execution loop (default: 5)")
    parser.add_argument("--max-review-rounds", type=int, default=3,
                        help="Maximum number of review rounds after tool execution (default: 3)")
    args = parser.parse_args()
    
    # Load config from environment variables
    config = BridgeConfig.from_env()
    
    # Override with command line arguments if provided
    if args.ollama_url:
        config.ollama.base_url = args.ollama_url
    if args.ghidra_url:
        config.ghidra.base_url = args.ghidra_url
    if args.model:
        config.ollama.model = args.model
    if args.mock:
        config.ghidra.mock_mode = True
        print("Running in MOCK mode - No GhidraMCP server required")
    
    # Pass the flag to the Bridge constructor
    bridge = Bridge(
        config, 
        include_capabilities=args.include_capabilities,
        max_agent_steps=args.max_steps,
        max_review_rounds=args.max_review_rounds
    )
    
    if args.health_check:
        status = bridge.health_check()
        print(f"Ollama Health: {'OK' if status['ollama'] else 'FAIL'}")
        print(f"GhidraMCP Health: {'OK' if status['ghidra'] else 'FAIL'}")
        sys.exit(0 if all(status.values()) else 1)
    
    if args.interactive:
        print("Ollama-GhidraMCP Bridge (Interactive Mode)")
        print(f"Using model: {config.ollama.model}")
        print(f"Capabilities included: {'Yes' if args.include_capabilities else 'No'}")
        print(f"Tool execution steps: {bridge.max_agent_steps}")
        print(f"Review rounds: {args.max_review_rounds if hasattr(bridge, 'max_review_rounds') else 3}")
        print("Type 'exit' or 'quit' to exit")
        
        while True:
            try:
                query = input("\nQuery: ")
                if query.lower() in ("exit", "quit"):
                    break
                    
                if query.lower() == "health":
                    status = bridge.health_check()
                    print(f"Ollama Health: {'OK' if status['ollama'] else 'FAIL'}")
                    print(f"GhidraMCP Health: {'OK' if status['ghidra'] else 'FAIL'}")
                    continue
                    
                response = bridge.process_query(query)
                print("\nResponse:")
                print(response)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                bridge.logger.error(f"Error: {str(e)}")
                print(f"Error: {str(e)}")
    else:
        # Non-interactive mode - read from stdin
        query = sys.stdin.read().strip()
        response = bridge.process_query(query)
        print(response)

if __name__ == "__main__":
    main() 