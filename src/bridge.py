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
import os  # Added import
from typing import Dict, Any, List, Optional

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
    
    def __init__(self, config: BridgeConfig, include_capabilities: bool = False):
        """
        Initialize the bridge.
        
        Args:
            config: BridgeConfig object with configuration settings
            include_capabilities: Flag to include capabilities in prompt
        """
        self.config = config
        self.logger = setup_logging(config)
        self.ollama = OllamaClient(config.ollama)
        self.ghidra = GhidraMCPClient(config.ghidra)
        self.context = []  # Store conversation context
        self.include_capabilities = include_capabilities  # Store the flag
        self.capabilities_text = self._load_capabilities_text()  # Load capabilities text on init
        self.logger.info(f"Bridge initialized with Ollama at {config.ollama.base_url} and GhidraMCP at {config.ghidra.base_url}")
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

    def process_query(self, query: str) -> str:
        """
        Process a natural language query through the AI and execute commands on GhidraMCP.
        
        Args:
            query: The user's query
            
        Returns:
            The processed response with command results
        """
        # Add the query to context
        self.context.append({"role": "user", "content": query})
        
        # Construct the base prompt from context
        context_prompt = "\n\n".join([
            f"{'User' if item['role'] == 'user' else 'Assistant'}: {item['content']}" 
            for item in self.context[-self.config.context_limit:]  # Use context_limit from config
        ])
        
        # Prepend capabilities if flag is set and text loaded
        capabilities_prefix = ""
        if self.include_capabilities and self.capabilities_text:
            capabilities_prefix = f"Context: Available Ghidra interaction tools and their functions:\n```\n{self.capabilities_text}\n```\n\n---\n\n"

        # Combine capabilities prefix, context, and final instruction
        full_prompt = capabilities_prefix + context_prompt 
        full_prompt += "\n\nPlease analyze the request based *only* on the provided context and available tools. Execute the necessary tool calls directly if appropriate."

        # Send to Ollama
        self.logger.info(f"Sending query to Ollama: {query[:100]}...")
        
        try:
            # Use the potentially modified full_prompt
            ai_response = self.ollama.generate(full_prompt, self.config.ollama.default_system_prompt)
            self.logger.info(f"Received response from Ollama: {ai_response[:100]}...")
            
            # Parse and execute commands
            result = self._parse_and_execute_commands(ai_response)
            
            # Add the processed response to context
            self.context.append({"role": "assistant", "content": result})
            
            return result
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            self.logger.error(error_msg)
            return f"Sorry, I encountered an error while processing your query: {str(e)}"
    
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
    parser.add_argument("--include-capabilities", action="store_true", help="Include capabilities context from ai_ghidra_capabilities.txt in prompts")
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
    bridge = Bridge(config, include_capabilities=args.include_capabilities)
    
    if args.health_check:
        status = bridge.health_check()
        print(f"Ollama Health: {'OK' if status['ollama'] else 'FAIL'}")
        print(f"GhidraMCP Health: {'OK' if status['ghidra'] else 'FAIL'}")
        sys.exit(0 if all(status.values()) else 1)
    
    if args.interactive:
        print("Ollama-GhidraMCP Bridge (Interactive Mode)")
        print(f"Using model: {config.ollama.model}")
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