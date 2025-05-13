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
import time
from typing import Dict, Any, List, Optional, Tuple, Union

from src.config import BridgeConfig
from src.ollama_client import OllamaClient
from src.ghidra_client import GhidraMCPClient
from src.command_parser import CommandParser
from src.cag.manager import CAGManager
from src import config

# Configure logging
def setup_logging(config):
    """Set up logging configuration."""
    handlers = []
    
    if config.log_console:
        handlers.append(logging.StreamHandler(sys.stdout))
        
    if config.log_file_enabled:
        handlers.append(logging.FileHandler(config.log_file))
        
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    return logging.getLogger("ollama-ghidra-bridge")

class Bridge:
    """Main bridge class that connects Ollama with GhidraMCP."""
    
    def __init__(self, config: BridgeConfig, include_capabilities: bool = False, max_agent_steps: int = 5,
                enable_cag: bool = True):
        """
        Initialize the bridge.
        
        Args:
            config: BridgeConfig object with configuration settings
            include_capabilities: Flag to include capabilities in prompt
            max_agent_steps: Maximum number of steps for tool execution
            enable_cag: Flag to enable Cache-Augmented Generation
        """
        self.config = config
        self.logger = setup_logging(config)
        self.ollama = OllamaClient(config.ollama)
        self.ghidra_client = GhidraMCPClient(config.ghidra)
        
        # Initialize context as a list for conversation history
        self.context = []
        
        self.include_capabilities = include_capabilities
        self.capabilities_text = self._load_capabilities_text()
        self.logger.info(f"Bridge initialized with Ollama at {config.ollama.base_url} and GhidraMCP at {config.ghidra.base_url}")
        self.max_agent_steps = max_agent_steps  # Maximum number of steps for tool execution
        
        # Initialize CAG Manager
        self.enable_cag = enable_cag
        self.cag_manager = CAGManager(config) if enable_cag else None
        if self.enable_cag:
            self.logger.info("Cache-Augmented Generation (CAG) enabled")
        
        # Internal state management - track what the agent has already done
        self.analysis_state = {
            'functions_decompiled': set(),  # Set of function addresses that have been decompiled
            'functions_renamed': {},        # Dict mapping original addresses to new names
            'comments_added': {},           # Dict mapping addresses to comments
            'functions_analyzed': set(),    # Set of functions that have been analyzed
        }
        
        # Planning state
        self.current_plan = None
        
        # Store partial outputs for building a cohesive final report
        self.partial_outputs = []
        
        # Planned tools tracker - track which tools are planned and executed
        self.planned_tools_tracker = {
            'planned': [],  # List of planned tool calls [{'tool': name, 'params': {}, 'execution_status': 'pending'}]
            'executed': [],  # List of executed tool calls [{'tool': name, 'params': {}}]
            'pending_critical': []  # List of critical planned tools that haven't been executed yet
        }
        
        # Current goal tracking
        self.current_goal = None
        self.goal_achieved = False
        self.goal_steps_taken = 0
        self.max_goal_steps = config.max_steps
        
        if self.include_capabilities and self.capabilities_text:
            self.logger.info("Capabilities context will be included in prompts.")
        elif self.include_capabilities:
            self.logger.warning("`--include-capabilities` flag set, but `ai_ghidra_capabilities.txt` not found or empty.")
        
        # Set up command parser
        self.command_parser = CommandParser()
        
        # Configure the bridge
        self.max_steps = getattr(config, 'MAX_STEPS', 5)
        self.max_goal_steps = getattr(config, 'MAX_GOAL_STEPS', 5)
        self.max_review_steps = getattr(config, 'MAX_REVIEW_STEPS', 5)
        self.enable_review = getattr(config, 'ENABLE_REVIEW', True)
    
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

    def _build_structured_prompt(self, phase: str = None) -> str:
        """
        Build a structured prompt with clear sections for capabilities, history, current task,
        and phase-specific guidance.
        
        Args:
            phase: Optional phase name to customize the prompt
            
        Returns:
            A structured prompt string with labeled sections
        """
        # Initialize all sections with empty strings
        capabilities_section = ""
        state_section = ""
        plan_section = ""
        cag_section = ""
        history_section = ""
        instructions_section = ""
        
        # Capabilities section
        if self.include_capabilities and self.capabilities_text:
            capabilities_section = (
                f"## Available Tools:\n"
                f"You have access to the following Ghidra interaction tools. "
                f"Use the `EXECUTE: tool_name(param1=value1, ...)` format to call them.\n"
                f"```text\n{self.capabilities_text}\n```\n---\n\n"
            )
        
        # State information section - what the agent has already done
        if any(len(v) > 0 for v in self.analysis_state.values() if isinstance(v, (dict, set))):
            state_section = "## Analysis State:\n"
            if self.analysis_state['functions_decompiled']:
                state_section += f"- Already decompiled functions: {', '.join(sorted(self.analysis_state['functions_decompiled']))}\n"
            if self.analysis_state['functions_renamed']:
                renamed = [f"{old} -> {new}" for old, new in self.analysis_state['functions_renamed'].items()]
                state_section += f"- Already renamed functions: {', '.join(renamed)}\n"
            if self.analysis_state['comments_added']:
                state_section += f"- Comments have been added to: {', '.join(sorted(self.analysis_state['comments_added'].keys()))}\n"
            if self.analysis_state['functions_analyzed']:
                state_section += f"- Already analyzed functions: {', '.join(sorted(self.analysis_state['functions_analyzed']))}\n"
            state_section += "---\n\n"
            
        # Current plan section
        if self.current_plan:
            plan_section = f"## Current Plan:\n{self.current_plan}\n---\n\n"
            
        # Conversation history section
        history_items = []
        
        # Get context history, handling both list and dict formats
        context_history = []
        if isinstance(self.context, list):
            context_history = self.context[-self.config.context_limit:]
        elif isinstance(self.context, dict) and 'history' in self.context:
            context_history = self.context['history'][-self.config.context_limit:]
        
        for item in context_history:
            prefix = "User: " if item["role"] == "user" else \
                    "Assistant: " if item["role"] == "assistant" else \
                    "Tool Call: " if item["role"] == "tool_call" else \
                    "Tool Result: " if item["role"] == "tool_result" else \
                    "Plan: " if item["role"] == "plan" else \
                    "Summary: " if item["role"] == "summary" else \
                    f"{item['role'].capitalize()}: "
            history_items.append(f"{prefix}{item['content']}")
        
        history_section = "## Conversation History:\n" + "\n".join(history_items) + "\n---\n\n"
        
        # CAG section - enhanced context from knowledge and session caches
        if self.enable_cag and self.cag_manager:
            # Get the latest user query from context
            latest_user_query = None
            
            if isinstance(self.context, list):
                for item in reversed(self.context):
                    if item["role"] == "user":
                        latest_user_query = item["content"]
                        break
            elif isinstance(self.context, dict) and 'history' in self.context:
                for item in reversed(self.context['history']):
                    if item["role"] == "user":
                        latest_user_query = item["content"]
                        break
            
            if latest_user_query:
                # Update session cache with latest context
                self.cag_manager.update_session_from_bridge_context(
                    self.context if isinstance(self.context, list) else self.context.get('history', [])
                )
                
                # Get enhanced context from CAG
                cag_context = self.cag_manager.enhance_prompt(latest_user_query, phase)
                if cag_context:
                    cag_section = f"## Enhanced Context:\n{cag_context}\n---\n\n"
        
        # Instructions section based on the current phase
        if phase == "planning":
            instructions_section = (
                "## Planning Instructions:\n"
                "1. Analyze the user request carefully\n"
                "2. Create a detailed plan for addressing the query\n"
                "3. Identify what information needs to be gathered from Ghidra\n"
                "4. Specify which tools will be needed and in what order\n"
                "5. Do NOT execute any commands yet - just create a plan\n"
                "---\n\n"
            )
        elif phase == "execution" or (not phase and self.current_plan):
            # If we're in execution phase or no specific phase with a plan already created
            instructions_section = (
                "## Tool Execution Instructions:\n"
                "1. Follow the plan to execute necessary Ghidra tools\n"
                "2. Use tools by writing `EXECUTE: tool_name(param1=value1, ...)` for each tool call\n"
                "3. IMPORTANT FOR RENAME OPERATIONS: When using rename_function_by_address, "
                "the function_address parameter must be the numerical address (e.g., '1800011a8'), not the function name (e.g., 'FUN_1800011a8')\n"
                "4. Focus on gathering information, not on analyzing it yet\n"
                "5. Execute the tools in a logical sequence\n"
                "---\n\n"
            )
        elif phase == "analysis":
            instructions_section = (
                "## Analysis Instructions:\n"
                "1. Analyze all the information gathered from the tool executions\n"
                "2. Connect different pieces of information to form a coherent understanding\n"
                "3. Focus on answering the user's original question comprehensively\n"
                "4. Format your answer clearly and concisely\n"
                "5. Prefix your final answer with 'FINAL RESPONSE:' to indicate completion\n"
                "---\n\n"
            )
        else:
            # Default instructions
            instructions_section = (
                "## Instructions:\n"
                "1. Analyze the user request carefully based on available context\n"
                "2. Use tools by writing `EXECUTE: tool_name(param1=value1, ...)` for each tool call\n"
                "3. IMPORTANT FOR RENAME OPERATIONS: When using rename_function_by_address, "
                "the function_address parameter must be the numerical address (e.g., '1800011a8'), not the function name (e.g., 'FUN_1800011a8')\n"
                "4. Provide analysis along with your tool calls\n"
                "5. Your response should be clear and concise\n"
                "6. When you have completed your analysis, include \"FINAL RESPONSE:\" followed by your complete answer\n"
                "---\n\n"
            )
        
        # Create the full prompt
        full_prompt = capabilities_section + state_section + plan_section + cag_section + history_section + instructions_section
        
        # Add final context for user queries
        latest_user_role = None
        latest_user_content = None
        
        if isinstance(self.context, list) and self.context:
            latest_user_role = self.context[-1].get("role")
            latest_user_content = self.context[-1].get("content")
        elif isinstance(self.context, dict) and self.context.get('history', []):
            latest_item = self.context['history'][-1]
            latest_user_role = latest_item.get("role")
            latest_user_content = latest_item.get("content")
            
        if latest_user_role == "user":
            if phase == "planning" or not self.current_plan:
                full_prompt += "## User Query:\nPlease create a plan to address this query. Do not execute any commands yet.\n"
            elif phase == "execution":
                full_prompt += "## User Query:\nPlease execute the necessary tools to gather information for this query.\n"
            elif phase == "analysis":
                full_prompt += "## User Query:\nPlease analyze the gathered information and provide a comprehensive answer.\n"
            else:
                full_prompt += "## User Query:\nPlease address this query using the available tools.\n"
            
        return full_prompt
    
    def _check_final_response_quality(self, response: str) -> bool:
        """
        Check if the final response is of good quality and doesn't indicate tool limitations.
        Also verifies that all critical planned tools have been executed.
        
        Args:
            response: The potential final response text
            
        Returns:
            True if the response is complete and satisfactory, False if it indicates incomplete analysis
        """
        # Look for phrases that indicate the model couldn't complete the task
        limitation_phrases = [
            "i cannot", "cannot directly", "i'm unable to", "unable to", 
            "doesn't include", "not available", "no way to", "would need",
            "don't have access", "no access to", "not possible with",
            "not able to", "couldn't find", "missing", "not found",
            "not supported", "no tool", "no command", "doesn't exist",
            "the current toolset doesn't"
        ]
        
        # Check if the response contains any of these limitation phrases
        response_lower = response.lower()
        for phrase in limitation_phrases:
            if phrase in response_lower:
                self.logger.info(f"Final response indicates limitation: '{phrase}'")
                return False
                
        # Check if response is too short
        if len(response.strip()) < 150:
            self.logger.info(f"Final response is too short ({len(response.strip())} chars)")
            return False
            
        # Check if final response has error messages
        if "ERROR:" in response or "Failed" in response:
            self.logger.info("Final response contains error messages")
            return False
            
        # Check if all critical planned tools have been executed
        # Update the pending_critical list based on current execution status
        pending_critical = [
            tool for tool in self.planned_tools_tracker['planned'] 
            if tool['is_critical'] and tool['execution_status'] == 'pending'
        ]
        
        if pending_critical:
            tool_names = ", ".join([tool['tool'] for tool in pending_critical])
            self.logger.info(f"Critical planned tools not executed: {tool_names}")
            
            # Check if the response falsely claims actions that weren't performed
            for tool in pending_critical:
                tool_name = tool['tool']
                # Check for phrases that indicate the tool was used when it actually wasn't
                false_claim_patterns = [
                    f"renamed to", f"renamed the function", f"function is now named",
                    f"have renamed", f"renamed", f"new name", f"changed the name",
                    f"added comment", f"commented", f"set a comment",
                    f"decompiled"
                ]
                
                for pattern in false_claim_patterns:
                    if pattern in response_lower and any(rename_tool in tool_name for rename_tool in ["rename", "comment"]):
                        self.logger.warning(f"Response falsely claims an action was performed: '{pattern}' but {tool_name} was not executed")
                        return False
            
            # If the response doesn't falsely claim completion but critical tools are missing, still return False
            return False
            
        return True

    def _normalize_command_name(self, command_name: str) -> str:
        """
        Normalize a command name (e.g., convert camelCase to snake_case).
        
        Args:
            command_name: The command name to normalize
            
        Returns:
            The normalized command name or empty string if not found
        """
        # First check if the command name already exists
        if hasattr(self.ghidra_client, command_name):
            return command_name
            
        # Try converting camelCase to snake_case
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', command_name).lower()
        
        # Only return the snake_case version if it exists
        if hasattr(self.ghidra_client, snake_case):
            logging.info(f"Normalized command name from '{command_name}' to '{snake_case}'")
            return snake_case
        
        return ""

    def _check_command_exists(self, command_name: str) -> Tuple[bool, str, List[str]]:
        """
        Check if a command exists and provide suggestions if it doesn't.
        
        Args:
            command_name: The command name to check
            
        Returns:
            Tuple of (exists, error_message, similar_commands)
        """
        normalized_command = self._normalize_command_name(command_name)
        if normalized_command:
            return True, "", []
            
        # Command not found, provide helpful suggestions
        available_commands = [
            name for name in dir(self.ghidra_client) 
            if not name.startswith('_') and callable(getattr(self.ghidra_client, name))
        ]
        
        # Find similar commands
        similar_commands = []
        for cmd in available_commands:
            # Simple similarity check - could be improved
            if command_name.lower() in cmd.lower() or cmd.lower() in command_name.lower():
                similar_commands.append(cmd)
        
        suggestion_msg = ""
        if similar_commands:
            suggestion_msg = f"\nDid you mean one of these? {', '.join(similar_commands)}"
            
        if command_name == "decompile":
            suggestion_msg = "\nDid you mean 'decompile_function(name=\"function_name\")' or 'decompile_function_by_address(address=\"1400011a8\")'?"
        elif command_name == "disassemble":
            suggestion_msg = "\nThere is no 'disassemble' command. Try 'decompile_function_by_address(address=\"1400011a8\")' instead."
            
        error_message = f"Unknown command: {command_name}{suggestion_msg}"
        return False, error_message, similar_commands

    def _normalize_command_params(self, command_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize command parameters based on command requirements.
        
        Args:
            command_name: The normalized command name
            params: The original parameters
            
        Returns:
            Normalized parameters
        """
        normalized_params = {}
        
        # Common parameter name mappings
        param_mappings = {
            "functionAddress": "address",
            "function_address": "address",
            "functionName": "name",
            "function_name": "name",
            "oldName": "old_name",
            "newName": "new_name"
        }
        
        # Special case normalizations for specific commands
        command_specific_mappings = {
            "rename_function_by_address": {
                "function_address": "address"
            },
            "decompile_function_by_address": {
                "function_address": "address"
            }
        }
        
        # Apply command-specific normalizations first
        if command_name in command_specific_mappings:
            for orig_key, new_key in command_specific_mappings[command_name].items():
                if orig_key in params:
                    normalized_params[new_key] = params[orig_key]
                    logging.info(f"Normalized parameter '{orig_key}' to '{new_key}' for command '{command_name}'")
        
        # Then apply general normalizations
        for key, value in params.items():
            if key in normalized_params:
                continue  # Skip if already processed by command-specific normalization
                
            # Apply general parameter name mapping
            norm_key = param_mappings.get(key, key)
            if norm_key != key:
                logging.info(f"Normalized parameter '{key}' to '{norm_key}' for command '{command_name}'")
                
            normalized_params[norm_key] = value
            
        return normalized_params

    def execute_command(self, command_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command with parameters.
        
        Args:
            command_name: The name of the command to execute
            params: The parameters to pass to the command
            
        Returns:
            The result of the command execution
        """
        try:
            # Normalize command name and parameters
            normalized_command = self._normalize_command_name(command_name)
            if not normalized_command:
                exists, error_message, similar_commands = self._check_command_exists(command_name)
                if not exists:
                    raise ValueError(error_message)
                
            # Check for required parameters
            is_valid, error_message = self.command_parser.validate_command_parameters(
                normalized_command, params
            )
            if not is_valid:
                enhanced_error = self.command_parser.get_enhanced_error_message(
                    command_name, params, error_message
                )
                raise ValueError(enhanced_error)
                
            # Find the command in the Ghidra client
            command_func = getattr(self.ghidra_client, normalized_command)
            
            # Execute the command
            return command_func(**params)
        except Exception as e:
            error_message = str(e)
            enhanced_error = self.command_parser.get_enhanced_error_message(
                command_name, params, error_message
            )
            raise ValueError(enhanced_error) from e

    def process_query(self, query: str) -> str:
        """
        Process a natural language query by planning, executing tools, and analyzing results.
        
        Args:
            query: Natural language query from the user
            
        Returns:
            Result of processing the query
        """
        try:
            # Store the query as our current goal
            self.current_goal = query
            self.goal_achieved = False
            self.goal_steps_taken = 0
            
            # Ensure context is initialized as a list if it's not already
            if not isinstance(self.context, list):
                if isinstance(self.context, dict) and 'history' in self.context:
                    self.context = self.context['history']
                else:
                    self.context = []
            
            # Add user query to context
            self.add_to_context("user", query)
            
            # PHASE 1: Planning - determine what tools need to be called
            plan_response = self._generate_plan(query)
            
            # PHASE 2: Tool Execution - call the tools based on the plan
            result = self._execute_plan()
            
            # PHASE 3: Analysis - analyze results and generate final response
            response = self._generate_analysis(query, result)
            
            # Add assistant response to context
            self.add_to_context("assistant", response)
            
            return response
        except Exception as e:
            # Log the exception
            logging.error(f"Error in query processing: {str(e)}")
            
            # Return error message
            return f"Error in query processing: {str(e)}"

    def _generate_plan(self, query: str) -> str:
        """
        Generate a plan for addressing the query using Ollama.
        
        Args:
            query: Natural language query from the user
            
        Returns:
            Plan response
        """
        # Use CAG manager to enhance context with knowledge and session data
        if self.enable_cag and self.cag_manager:
            # Update session cache with current context
            self.cag_manager.update_session_from_bridge_context(self.context)
        
        logging.info("Starting planning phase")
        
        # Build prompt
        prompt = self._build_structured_prompt(phase="planning") + f"\nUser Query: {query}"
        
        # Generate planning response
        response = self.ollama.generate_with_phase(prompt, phase="planning")
        
        # Extract plan
        self.current_plan = response
        logging.info(f"Received planning response: {response[:100]}...")
        
        # Parse the planned tools
        self.current_plan_tools = self._parse_plan_tools(response)
        logging.info(f"Extracted {len(self.current_plan_tools)} planned tools from plan")
        
        # Add plan to context
        self.add_to_context("plan", response)
        
        logging.info("Planning phase completed")
        return response

    def _display_tool_result(self, cmd_name: str, result: Any) -> None:
        """
        Display a tool result to the user in a clear, formatted way.
        
        Args:
            cmd_name: The name of the command executed
            result: The result from the command execution
        """
        # List of "verbose" commands that should display their full results
        verbose_commands = ["list_functions", "list_methods", "list_imports", "list_exports", 
                           "search_functions_by_name", "decompile_function", "decompile_function_by_address"]
        
        # Special handling based on command type
        if cmd_name in verbose_commands:
            print("\n" + "="*60)
            print(f"Results from {cmd_name}:")
            print("="*60)
            
            # Format based on result type
            if isinstance(result, list):
                # For lists like function lists, show with numbering
                for i, item in enumerate(result, 1):
                    if isinstance(item, dict) and "name" in item and "address" in item:
                        print(f"{i:3d}. {item['name']} @ {item['address']}")
                    elif isinstance(item, dict):
                        print(f"{i:3d}. {item}")
                    else:
                        print(f"{i:3d}. {item}")
                print(f"\nTotal: {len(result)} items")
            elif isinstance(result, dict):
                # For dictionary results
                for key, value in result.items():
                    print(f"{key}: {value}")
            elif isinstance(result, str) and len(result) > 500:
                # For long string results (like decompiled code)
                print(f"{result[:500]}...\n[Showing first 500 characters of {len(result)} total]")
            else:
                # For other results
                print(result)
            
            print("="*60 + "\n")
        else:
            # For non-verbose commands, just show a success message
            print(f"✓ Successfully executed {cmd_name}")
            
    def _execute_plan(self) -> str:
        """
        Execute the plan by processing each tool in sequence.
        
        Returns:
            Combined results of all tool executions
        """
        logging.info("Starting execution phase")
        
        all_results = []
        self.goal_steps_taken = 0
        step_count = 0
        goal_statement = f"Goal: {self.current_goal}"
        
        # Loop until we hit max steps or goal is achieved
        while step_count < self.max_goal_steps and not self.goal_achieved:
            step_count += 1
            self.goal_steps_taken = step_count
            
            logging.info(f"Step {step_count}/{self.max_goal_steps}: Sending query to Ollama")
            
            # Build prompt for tool execution, including the goal and current state
            state_context = self._build_structured_prompt(phase="execution")
            prompt = f"{state_context}\n{goal_statement}\nStep {step_count}: Determine the next tool to call or mark the goal as completed."
            
            # Use CAG to enhance context with knowledge and session data
            if self.enable_cag and self.cag_manager:
                # Update session cache with current context
                self.cag_manager.update_session_from_bridge_context(self.context)
            
            # Generate execution step
            response = self.ollama.generate_with_phase(prompt, phase="execution")
            logging.info(f"Received response from Ollama: {response[:100]}...")
            
            # Extract commands to execute
            commands = self.command_parser.extract_commands(response)
            
            # If no commands but the response indicates goal completion, mark as achieved
            if not commands and ("GOAL ACHIEVED" in response.upper() or "GOAL COMPLETE" in response.upper()):
                logging.info("AI indicates the goal has been achieved")
                self.goal_achieved = True
                all_results.append(f"Step {step_count} - Goal achievement indicated: {response}")
                break
                
            # Execute commands
            execution_result = ""
            for cmd_name, cmd_params in commands:
                try:
                    # Add tool call to context
                    tool_call = f"EXECUTE: {cmd_name}({', '.join([f'{k}=\"{v}\"' for k, v in cmd_params.items()])})"
                    self.add_to_context("tool_call", tool_call)
                    
                    # Execute command with parameter normalization
                    logging.info(f"Executing GhidraMCP command: {cmd_name} with params: {cmd_params}")
                    result = self.execute_command(cmd_name, cmd_params)
                    
                    # Display the result to the user
                    self._display_tool_result(cmd_name, result)
                    
                    # Format the result for context and logging
                    if isinstance(result, dict) or isinstance(result, list):
                        execution_result = json.dumps(result, indent=2)
                    else:
                        execution_result = str(result)
                    
                    # Add command result to context
                    self.add_to_context("tool_result", execution_result)
                    
                    # Update analysis state
                    command = {"name": cmd_name, "params": cmd_params}
                    self._update_analysis_state(command, execution_result)
                    
                    # Add to all results
                    all_results.append(f"Command: {cmd_name}\nResult: {execution_result}\n")
                
                except Exception as e:
                    error_msg = f"ERROR: {str(e)}"
                    logging.error(f"Error executing {cmd_name}: {error_msg}")
                    execution_result = error_msg
                    self.add_to_context("tool_error", error_msg)
                    all_results.append(f"Command: {cmd_name}\nError: {error_msg}\n")
                    print(f"❌ Error executing {cmd_name}: {error_msg}")
            
            # If no commands were found, note this and end loop if it's the second consecutive time
            if not commands:
                logging.info("No commands found in AI response, ending tool execution loop")
                all_results.append(f"Step {step_count} - No tool calls: {response}")
                break
        
        if step_count >= self.max_goal_steps:
            logging.info(f"Reached maximum steps ({self.max_goal_steps}), ending tool execution loop")
            
        logging.info("Execution phase completed")
        return "\n".join(all_results)

    def _evaluate_goal_completion(self, query: str, execution_results: str) -> bool:
        """
        Evaluate whether the current goal has been achieved based on execution results.
        
        Args:
            query: The original query/goal
            execution_results: Results from tool executions
            
        Returns:
            True if goal is achieved, False otherwise
        """
        logging.info("Evaluating goal completion")
        
        # Build prompt for goal evaluation
        state_context = self._build_structured_prompt(phase="evaluation")
        prompt = f"{state_context}\nGoal: {query}\nExecution Results:\n{execution_results}\n\nQuestion: Has the goal been achieved? Respond with 'GOAL ACHIEVED' if yes, or 'GOAL NOT ACHIEVED' if more tool calls are needed."
        
        # Generate evaluation response
        response = self.ollama.generate_with_phase(prompt, phase="execution")
        
        # Check if goal is achieved
        goal_achieved = "GOAL ACHIEVED" in response.upper()
        logging.info(f"Goal evaluation: {'Achieved' if goal_achieved else 'Not achieved'}")
        
        return goal_achieved

    def _clean_final_response(self, response: str) -> str:
        """
        Clean up the final response for display by removing markers and formatting.
        
        Args:
            response: The raw final response
            
        Returns:
            Cleaned response text
        """
        # Remove "FINAL RESPONSE:" marker if present
        cleaned = re.sub(r'^FINAL RESPONSE:\s*', '', response, flags=re.IGNORECASE)
        
        # Remove any trailing instructions or markers
        cleaned = re.sub(r'\n+\s*EXECUTE:.*$', '', cleaned, flags=re.MULTILINE)
        
        # Remove any markdown formatting intended for the AI but not for display
        cleaned = re.sub(r'^\s*```.*?```\s*$', '', cleaned, flags=re.MULTILINE | re.DOTALL)
        
        return cleaned.strip()

    def _generate_analysis(self, query: str, execution_results: str) -> str:
        """
        Analyze the results of tool executions and generate a final response.
        
        Args:
            query: The original query
            execution_results: Results from tool executions
            
        Returns:
            Final analysis response
        """
        logging.info("Starting review and reasoning phase")
        
        self.goal_achieved = False
        review_steps = 0
        max_review_steps = self.max_goal_steps
        final_response = ""
        review_results = []
        
        # Phase to iteratively review and refine our understanding
        while not self.goal_achieved and review_steps < max_review_steps:
            review_steps += 1
            logging.info(f"Review step {review_steps}/{max_review_steps}: Sending query to Ollama")
            
            # Build prompt for review
            state_context = self._build_structured_prompt(phase="review")
            current_goal = f"Goal: {self.current_goal}"
            review_prompt = f"{state_context}\n{current_goal}\nExecution Results:\n{execution_results}\n\nReview the results and provide analysis. If you need to execute more tools, use the EXECUTE format. Otherwise, provide your FINAL RESPONSE when you've fully addressed the goal."
            
            # Use CAG to enhance context
            if self.enable_cag and self.cag_manager:
                self.cag_manager.update_session_from_bridge_context(self.context)
            
            # Generate review response
            review_response = self.ollama.generate_with_phase(review_prompt, phase="analysis")
            logging.info(f"Received review response: {review_response[:100]}...")
            
            # Check for the final response marker
            final_response_match = re.search(r'FINAL RESPONSE:\s*(.*?)(?:\n\s*$|\Z)', 
                                             review_response, re.DOTALL)
            if final_response_match:
                final_response = final_response_match.group(1).strip()
                
                # Validate that the final response is reasonable
                if final_response and len(final_response) > 100:
                    logging.info("Found high-quality 'FINAL RESPONSE' marker in review, ending review loop")
                    self.goal_achieved = True
                    break
                elif final_response:
                    if "unable" in final_response.lower() or "limit" in final_response.lower():
                        logging.info(f"Final response is too short ({len(final_response)} chars)")
                        logging.info("Found 'FINAL RESPONSE' marker but response indicates limitations, continuing review")
                else:
                    logging.info("'FINAL RESPONSE' marker found but unable to extract response")
            
            # Check for additional tool calls in the review
            commands = self.command_parser.extract_commands(review_response)
            if commands:
                for cmd_name, cmd_params in commands:
                    try:
                        # Execute command
                        result = self.execute_command(cmd_name, cmd_params)
                        
                        # Format result for display
                        formatted_result = self.command_parser.format_command_results(cmd_name, cmd_params, result)
                        logging.info(f"Review command executed: {cmd_name}")
                        
                        # Add result to context
                        self.add_to_context("tool_result", formatted_result)
                        
                        review_results.append(f"Tool Call: {cmd_name}\nTool Result: {formatted_result}\n")
                    except Exception as e:
                        error_msg = f"ERROR: {str(e)}"
                        logging.error(f"Error executing review command {cmd_name}: {error_msg}")
                        self.add_to_context("tool_error", error_msg)
                        review_results.append(f"Error executing {cmd_name}: {error_msg}")
            
            # If no commands and no final response yet, continue
            if not commands and not final_response:
                review_results.append(f"Review step {review_steps}: {review_response}")
        
        # If we have a final response, add it to the results
        if final_response:
            # Clean up the response for display
            display_response = self._clean_final_response(final_response)
            review_results.append(f"FINAL RESPONSE:\n{display_response}")
        else:
            review_results.append("No final response generated during review")
            
        return "\n".join(review_results)

    def _update_analysis_state(self, command: Dict[str, Any], result: str) -> None:
        """
        Update the internal analysis state based on the executed command and result.
        
        Args:
            command: The executed command
            result: The result of the command
        """
        # Only update state if command was successful
        if "ERROR" in result or "Failed" in result:
            return
            
        # Track decompiled functions
        if command['name'] == "decompile_function" and "name" in command['params']:
            self.analysis_state['functions_analyzed'].add(command['params']['name'])
            
        elif command['name'] == "decompile_function_by_address" and "address" in command['params']:
            address = command['params']['address']
            self.analysis_state['functions_decompiled'].add(address)
            self.analysis_state['functions_analyzed'].add(address)
            
        # Track renamed functions
        elif command['name'] == "rename_function" and "old_name" in command['params'] and "new_name" in command['params']:
            self.analysis_state['functions_renamed'][command['params']['old_name']] = command['params']['new_name']
            
        elif command['name'] == "rename_function_by_address" and "function_address" in command['params'] and "new_name" in command['params']:
            self.analysis_state['functions_renamed'][command['params']['function_address']] = command['params']['new_name']
            
        # Track comments added
        elif command['name'] in ["set_decompiler_comment", "set_disassembly_comment"] and "address" in command['params'] and "comment" in command['params']:
            self.analysis_state['comments_added'][command['params']['address']] = command['params']['comment']
    
    def _check_for_clarification_request(self, response: str) -> bool:
        """
        Check if the AI's response is a request for clarification from the user.
        
        Args:
            response: The AI's response text
            
        Returns:
            True if the response is a clarification request, False otherwise
        """
        # Simple heuristic: look for question marks near the end of the response
        # and check if the response doesn't contain any tool calls
        if "EXECUTE:" not in response and "?" in response:
            last_paragraph = response.split("\n\n")[-1].strip()
            # If the last paragraph ends with a question mark, it's likely a clarification request
            if last_paragraph.endswith("?"):
                # Additional check: make sure it's not just showing code examples with question marks
                if not ("`" in last_paragraph or "```" in last_paragraph):
                    return True
        return False
        
    def _extract_suggestions(self, response: str) -> Tuple[str, List[str]]:
        """
        Extract tool improvement suggestions from the AI's response.
        
        Args:
            response: The AI's response text
            
        Returns:
            Tuple of (cleaned_response, list_of_suggestions)
        """
        suggestions = []
        cleaned_lines = []
        
        # Simple parsing: look for lines starting with "SUGGESTION:"
        for line in response.split("\n"):
            if line.strip().startswith("SUGGESTION:"):
                suggestion = line.strip()[len("SUGGESTION:"):].strip()
                suggestions.append(suggestion)
            else:
                cleaned_lines.append(line)
                
        # If suggestions were found, log them
        if suggestions:
            self.logger.info(f"Found {len(suggestions)} tool improvement suggestions")
            for suggestion in suggestions:
                self.logger.info(f"Tool suggestion: {suggestion}")
                
        return "\n".join(cleaned_lines), suggestions

    def _generate_cohesive_report(self) -> str:
        """
        Generate a cohesive report from various data gathered during the analysis.
        
        Returns:
            A comprehensive report as a string
        """
        if not self.partial_outputs:
            return "No analysis was performed or captured."
            
        # Organize our partial outputs into sections for the report
        report_sections = {
            "plan": [],              # Added section for the initial plan
            "findings": [],
            "insights": [],
            "analysis": [],
            "tools": [],
            "errors": [],            # Added section for errors
            "conclusions": []
        }
        
        # First, process the raw responses to capture information that might be truncated in cleaned responses
        raw_responses = []
        for output in self.partial_outputs:
            if output["type"] in ["raw_response", "raw_review"]:
                raw_responses.append(output["content"])
        
        # Process partial outputs to populate sections
        for output in self.partial_outputs:
            content = output.get("content", "")
            output_type = output.get("type", "")
            
            # --- Capture Initial Plan ---
            if output_type == "planning":
                report_sections["plan"].append(content)
                continue # Skip further processing for plan content
                
            # --- Process Reasoning (Cleaned & Raw) ---
            if output_type in ["reasoning", "review"]:
                # Use the cleaned reasoning/review content for keyword/structure matching
                
                # Extract numbered insights
                numbered_insights = []
                in_numbered_list = False
                current_insight = ""
                for line in content.split('\n'):
                    if re.match(r'^\s*\d+\.\s', line):
                        if in_numbered_list and current_insight.strip(): numbered_insights.append(current_insight.strip())
                        in_numbered_list = True
                        current_insight = line.strip()
                    elif in_numbered_list and line.strip(): current_insight += " " + line.strip()
                    elif in_numbered_list: # End of item
                        if current_insight.strip(): numbered_insights.append(current_insight.strip())
                        in_numbered_list = False
                        current_insight = ""
                if in_numbered_list and current_insight.strip(): numbered_insights.append(current_insight.strip())
                if numbered_insights: report_sections["insights"].extend(numbered_insights)
                
                # Extract bulleted findings
                findings_section = False
                for line in content.split('\n'):
                    if any(marker in line.lower() for marker in ["i found:", "findings:", "key observations:", "key finding"]):
                        findings_section = True
                    elif findings_section and not line.strip(): findings_section = False
                    if findings_section or line.strip().startswith('- ') or line.strip().startswith('* '):
                        if line.strip(): report_sections["findings"].append(line.strip())
                        
                # Extract conclusions
                if any(marker in content.lower() for marker in ["in conclusion", "to summarize", "in summary", "conclusion:", "final analysis"]):
                    conclusion_text = ""
                    in_conclusion = False
                    for line in content.split('\n'):
                        if any(marker in line.lower() for marker in ["in conclusion", "to summarize", "in summary", "conclusion:", "final analysis"]):
                            in_conclusion = True
                        if in_conclusion and line.strip(): conclusion_text += line + "\n"
                    if conclusion_text: report_sections["conclusions"].append(conclusion_text.strip())
                
                # Extract general analysis (exclude already captured parts)
                analysis_content = content
                for category in ["findings", "insights", "conclusions"]:
                    for item in report_sections[category]:
                        analysis_content = analysis_content.replace(item, "")
                if analysis_content.strip():
                    # Only add if it contains relevant technical terms
                    if any(term in analysis_content.lower() for term in ["function", "address", "import", "export", "binary", "assembly", "code", "decompile", "call", "pointer", "struct"]):
                        report_sections["analysis"].append(analysis_content.strip())
        
        # --- Process Raw Responses for Additional Detail (before EXECUTE) ---
        for raw_response in raw_responses:
            # Extract text before the first EXECUTE block
            pre_execute_text = raw_response.split("EXECUTE:", 1)[0].strip()
            if not pre_execute_text:
                continue
            
            # Extract numbered insights from raw text
            numbered_insights_raw = []
            in_numbered_list_raw = False
            current_insight_raw = ""
            for line in pre_execute_text.split('\n'):
                if re.match(r'^\s*\d+\.\s', line):
                    if in_numbered_list_raw and current_insight_raw.strip(): numbered_insights_raw.append(current_insight_raw.strip())
                    in_numbered_list_raw = True
                    current_insight_raw = line.strip()
                elif in_numbered_list_raw and line.strip(): current_insight_raw += " " + line.strip()
                elif in_numbered_list_raw:
                    if current_insight_raw.strip(): numbered_insights_raw.append(current_insight_raw.strip())
                    in_numbered_list_raw = False
                    current_insight_raw = ""
            if in_numbered_list_raw and current_insight_raw.strip(): numbered_insights_raw.append(current_insight_raw.strip())
            if numbered_insights_raw: report_sections["insights"].extend(numbered_insights_raw)
            
            # Extract bulleted findings from raw text
            for line in pre_execute_text.split('\n'):
                 if (line.strip().startswith('- ') or line.strip().startswith('* ')):
                     if line.strip(): report_sections["findings"].append(line.strip())
                     
            # Extract general analysis from raw text (exclude already captured parts)
            analysis_content_raw = pre_execute_text
            for category in ["findings", "insights"]:
                for item in report_sections[category]:
                    analysis_content_raw = analysis_content_raw.replace(item, "")
            if analysis_content_raw.strip():
                 if any(term in analysis_content_raw.lower() for term in ["function", "address", "import", "export", "binary", "assembly", "code", "decompile", "call", "pointer", "struct"]):
                     report_sections["analysis"].append(analysis_content_raw.strip())
        
        # --- Process Tool Results & Errors ---
        tool_results = []
        for output in self.partial_outputs:
            if output["type"] in ["tool_result", "review_tool_result"]:
                result_text = output.get("result", "")
                step_info = f"Step {output.get('step', output.get('review_step', '?'))}"
                tool_info = f"{output.get('tool', 'unknown')}({', '.join([f'{k}={v}' for k, v in output.get('params', {}).items()])})"
                
                # Check for errors
                if "ERROR:" in result_text or "Failed" in result_text:
                    report_sections["errors"].append(f"{step_info}: {tool_info} -> {result_text}")
                else:
                    # Successful result - summarize and add to tools list
                    result_lines = result_text.split('\n')
                    # Remove the RESULT: prefix if present
                    result_content = '\n'.join([l.replace("RESULT: ", "", 1) for l in result_lines if l.strip()])
                    result_summary = result_content[:150] + ("..." if len(result_content) > 150 else "")
                    tool_results.append(f"{step_info}: {tool_info} -> {result_summary}")
        
        report_sections["tools"] = tool_results
        
        # --- Deduplicate Sections --- 
        for section in report_sections:
            if isinstance(report_sections[section], list):
                seen = set()
                # Keep order, filter duplicates (case-insensitive for strings)
                report_sections[section] = [x for x in report_sections[section] if not ( (x.lower() if isinstance(x, str) else x) in seen or seen.add( (x.lower() if isinstance(x, str) else x) ) )]
        
        # Option 1: Build a structured report manually
        report = self._build_structured_report(report_sections)
        
        # Return the manually structured report
        return report
        
    def _build_structured_report(self, report_sections):
        """
        Build a structured report from the collected sections.
        
        Args:
            report_sections: Dict of report sections
            
        Returns:
            A formatted report string
        """
        report = "# Analysis Report\n\n"
        
        if report_sections["plan"]:
            report += "## Initial Plan\n"
            report += "\n".join(report_sections["plan"]) + "\n\n"
        
        if report_sections["insights"]:
            report += "## Key Insights\n"
            report += "\n".join(report_sections["insights"]) + "\n\n"
        
        if report_sections["findings"]:
            report += "## Findings\n"
            report += "\n".join(report_sections["findings"]) + "\n\n"
        
        if report_sections["analysis"]:
            report += "## Analysis Details\n"
            report += "\n\n".join(report_sections["analysis"]) + "\n\n"
        
        if report_sections["tools"]:
            report += "## Tools Used (Successful)\n"
            report += "\n".join([f"- {tool}" for tool in report_sections["tools"]]) + "\n\n"
            
        if report_sections["errors"]:
            report += "## Errors Encountered\n"
            report += "\n".join([f"- {error}" for error in report_sections["errors"]]) + "\n\n"
        
        if report_sections["conclusions"]:
            report += "## Conclusions\n"
            report += "\n".join(report_sections["conclusions"]) + "\n"
        
        return report.strip()
    
    def _parse_plan_tools(self, plan: str) -> List[Dict[str, Any]]:
        """
        Parse the plan text to extract the planned tools.
        
        Args:
            plan: The plan text
            
        Returns:
            List of tool dictionaries, where each dictionary contains 'name' and 'params'
        """
        tools = []
        
        # Look for the PLAN: section
        if "PLAN:" in plan:
            plan_section = plan.split("PLAN:", 1)[1].strip()
            
            # Extract each line that starts with "TOOL: "
            lines = plan_section.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("TOOL: "):
                    try:
                        # Parse the tool line into name and params
                        tool_part = line[len("TOOL: "):].strip()
                        name_part, params_part = tool_part.split(" PARAMS: ", 1)
                        name = name_part.strip()
                        
                        # Parse parameters if any
                        params = {}
                        if params_part.strip():
                            param_pairs = params_part.split(", ")
                            for pair in param_pairs:
                                if "=" in pair:
                                    key, value = pair.split("=", 1)
                                    key = key.strip()
                                    value = value.strip()
                                    
                                    # Remove quotes from string values
                                    if value.startswith('"') and value.endswith('"'):
                                        value = value[1:-1]
                                        
                                    # Convert numeric values to integers if appropriate
                                    if value.isdigit():
                                        value = int(value)
                                        
                                    params[key] = value
                        
                        tools.append({
                            'name': name,
                            'params': params
                        })
                    except Exception as e:
                        logging.error(f"Error parsing tool line '{line}': {str(e)}")
        
        return tools

    def _mark_tool_as_executed(self, command_name: str, params: Dict[str, Any]) -> None:
        """
        Mark a tool as executed in the planned tools tracker.
        
        Args:
            command_name: The name of the executed command
            params: The parameters used for the command
        """
        for tool_entry in self.planned_tools_tracker['planned']:
            if tool_entry['tool'] == command_name:
                tool_entry['execution_status'] = 'executed'
                break

    def _get_pending_critical_tools_prompt(self) -> str:
        """
        Generate a prompt section about pending critical tools.
        
        Returns:
            A string to be included in the review prompt if there are pending critical tools
        """
        # Update the pending_critical list based on current execution status
        self.planned_tools_tracker['pending_critical'] = [
            tool for tool in self.planned_tools_tracker['planned'] 
            if tool['is_critical'] and tool['execution_status'] == 'pending'
        ]
        
        if not self.planned_tools_tracker['pending_critical']:
            return ""
            
        # Generate the prompt
        pending_tools_prompt = "\n\nThere are pending critical tool calls that appear necessary but have not been executed:\n"
        
        for tool in self.planned_tools_tracker['pending_critical']:
            pending_tools_prompt += f"- {tool['tool']}: Mentioned in context \"{tool['context']}\"\n"
            
        pending_tools_prompt += "\nPlease ensure these critical tool calls are explicitly executed before concluding the task."
        
        return pending_tools_prompt

    def _check_implied_actions_without_commands(self, response_text: str) -> str:
        """
        Check if the response text implies actions that should be taken but doesn't include 
        the actual EXECUTE commands to perform those actions.
        
        Args:
            response_text: The AI's response text
            
        Returns:
            A prompt string asking for explicit commands if needed, otherwise empty string
        """
        # Skip if there are already commands in the response
        if "EXECUTE:" in response_text:
            return ""
            
        # Check if this is a review prompt we generated - if so, don't re-analyze it
        if "Your response implies certain actions should be taken" in response_text:
            return ""
            
        # Patterns that indicate implied actions without explicit commands
        implied_action_patterns = [
            (r"(should|will|going to|let's) rename", "rename_function"),
            (r"(should|will|going to|let's) add comment", "set_decompiler_comment"),
            (r"(suggest|proposed|recommend) (naming|naming it|renaming)", "rename_function"),
            (r"(suggest|proposed|recommend) (to|that) name", "rename_function"),
            (r"(appropriate|suitable|better|good|descriptive) name would be", "rename_function"),
            (r"function (should|could|would) be (named|called)", "rename_function"),
            (r"rename (the|this) function (to|as)", "rename_function"),
            (r"naming it ['\"]([\w_]+)['\"]", "rename_function")
        ]
        
        response_lower = response_text.lower()
        
        # Check for implied actions
        implied_actions = []
        for pattern, related_tool in implied_action_patterns:
            if re.search(pattern, response_lower):
                implied_actions.append((pattern, related_tool))
                
        if not implied_actions:
            return ""
            
        # Generate a prompt asking for explicit commands
        action_prompt = "\n\nYour response implies certain actions should be taken, but you didn't include explicit EXECUTE commands:\n"
        
        for pattern, tool in implied_actions:
            matches = re.findall(pattern, response_lower)
            if matches:
                action_prompt += f"- You mentioned: '{pattern.replace('|', ' or ')}'\n"
                
        action_prompt += "\nPlease provide explicit EXECUTE commands to perform these actions."
        return action_prompt

    def add_to_context(self, role: str, content: str) -> None:
        """
        Add an entry to the context history.
        
        Args:
            role: The role of the entry ('user', 'assistant', 'tool_call', 'tool_result', etc.)
            content: The content of the entry
        """
        # Check if context is a list (old style) or dictionary (new style)
        if isinstance(self.context, list):
            self.context.append({"role": role, "content": content})
        elif isinstance(self.context, dict):
            if not 'history' in self.context:
                self.context['history'] = []
            self.context['history'].append({"role": role, "content": content})
        else:
            # Create a new list if neither
            self.context = [{"role": role, "content": content}]

    @property
    def ghidra(self):
        """Property for backward compatibility with code referencing bridge.ghidra."""
        return self.ghidra_client

    def execute_goal(self, goal: str) -> Tuple[bool, List[str]]:
        """
        Execute a goal by breaking it down into steps and executing each step.
        
        Args:
            goal: The goal to execute
            
        Returns:
            Tuple of (success, results)
        """
        logging.info(f"Executing goal: {goal}")
        self.context["goal"] = goal
        all_results = []
        step_count = 0
        self.goal_achieved = False

        # Use CAG manager to enhance context with knowledge and session data
        if self.enable_cag and self.cag_manager:
            # Update session cache with current context
            self.cag_manager.update_session_from_bridge_context(self.context)
        
        logging.info("Starting planning phase")
        planning_prompt = self._build_planning_prompt(goal)
        planning_response = self.chat_engine.query(planning_prompt)
        logging.info(f"Received planning response: {planning_response[:100]}...")
        
        # Extract tools from the plan
        planned_tools = self._extract_planned_tools(planning_response)
        logging.info(f"Extracted {len(planned_tools)} planned tools from plan")
        
        # Add the plan to context
        self.add_to_context("plan", planning_response)
        
        logging.info("Planning phase completed")
        logging.info("Starting execution phase")
        
        while step_count < self.max_goal_steps and not self.goal_achieved:
            step_count += 1
            logging.info(f"Step {step_count}/{self.max_goal_steps}: Sending query to Ollama")
            
            # Generate prompt based on current context
            prompt = self._build_execution_prompt()
            
            # Get response from Ollama
            response = self.chat_engine.query(prompt)
            logging.info(f"Received response from Ollama: {response[:100]}...")
            
            # Update context with the response
            self.add_to_context("execution_response", response)
            
            # Process commands in the response
            commands = self.command_parser.extract_commands(response)
            
            if self.is_goal_achieved(response):
                logging.info("Goal achievement indicated in response")
                self.goal_achieved = True
                all_results.append(f"Step {step_count} - Goal achievement indicated: {response}")
                break
                
            # Execute commands
            execution_result = ""
            for cmd_name, cmd_params in commands:
                try:
                    # Add tool call to context
                    tool_call = f"EXECUTE: {cmd_name}({', '.join([f'{k}=\"{v}\"' for k, v in cmd_params.items()])})"
                    self.add_to_context("tool_call", tool_call)
                    
                    # Execute command
                    result = self.execute_command(cmd_name, cmd_params)
                    
                    # Format result for display
                    formatted_result = self.command_parser.format_command_results(cmd_name, cmd_params, result)
                    logging.info(f"Command executed: {cmd_name}")
                    logging.info(f"Result: {formatted_result[:100]}...")
                    
                    # Add result to context
                    self.add_to_context("tool_result", formatted_result)
                    
                    execution_result = formatted_result
                    all_results.append(f"Command: {cmd_name}\nResult: {execution_result}\n")
                
                except Exception as e:
                    error_msg = f"ERROR: {str(e)}"
                    logging.error(f"Error executing {cmd_name}: {error_msg}")
                    execution_result = error_msg
                    self.add_to_context("tool_error", error_msg)
                    all_results.append(f"Error executing {cmd_name}: {error_msg}")
            
            # If no commands found, end the execution phase
            if not commands:
                logging.info("No commands found in AI response, ending tool execution loop")
                all_results.append(f"Step {step_count} - No tool calls: {response}")
                break
        
        if step_count >= self.max_goal_steps:
            logging.info(f"Reached maximum steps ({self.max_goal_steps}), ending tool execution loop")
            all_results.append(f"Reached maximum steps ({self.max_goal_steps})")
            
        logging.info("Execution phase completed")
        
        # Only do review if requested
        if self.enable_review:
            all_results.append("\n=== REVIEW PHASE ===\n")
            all_results.extend(self._perform_review_phase())
            
        return self.goal_achieved, all_results

    def _build_execution_prompt(self) -> str:
        """
        Build a prompt for the execution phase.
        
        Returns:
            The prompt string
        """
        # Include context, goal, and any previous interactions
        prompt = self._build_structured_prompt(phase="execution") 
        
        # Add function call best practices
        if hasattr(config, 'FUNCTION_CALL_BEST_PRACTICES') and config.FUNCTION_CALL_BEST_PRACTICES:
            prompt += f"\n\nFunction call best practices:\n{config.FUNCTION_CALL_BEST_PRACTICES}\n"
            
        return prompt

    def _build_planning_prompt(self, goal: str) -> str:
        """
        Build a prompt for the planning phase.
        
        Args:
            goal: The goal to plan for
            
        Returns:
            The prompt string
        """
        # Base system message
        prompt = self._build_structured_prompt(phase="planning") + f"\nGoal: {goal}\n"
        
        # Add function call best practices
        if hasattr(config, 'FUNCTION_CALL_BEST_PRACTICES') and config.FUNCTION_CALL_BEST_PRACTICES:
            prompt += f"\n\nFunction call best practices:\n{config.FUNCTION_CALL_BEST_PRACTICES}\n"
            
        return prompt
        
    def _build_review_prompt(self) -> str:
        """
        Build a prompt for the review phase.
        
        Returns:
            The prompt string
        """
        prompt = self._build_structured_prompt(phase="review")
        
        # Add function call best practices
        if hasattr(config, 'FUNCTION_CALL_BEST_PRACTICES') and config.FUNCTION_CALL_BEST_PRACTICES:
            prompt += f"\n\nFunction call best practices:\n{config.FUNCTION_CALL_BEST_PRACTICES}\n"
        
        return prompt

def main():
    """Main entry point for the bridge application."""
    parser = argparse.ArgumentParser(description="Ollama-GhidraMCP Bridge")
    parser.add_argument("--ollama-url", help="Ollama server URL")
    parser.add_argument("--ghidra-url", help="GhidraMCP server URL")
    parser.add_argument("--model", help="Ollama model to use")
    
    # Add model arguments for each phase
    parser.add_argument("--planning-model", help="Model to use for the planning phase")
    parser.add_argument("--execution-model", help="Model to use for the execution phase")
    parser.add_argument("--analysis-model", help="Model to use for the analysis phase")
    
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--list-context", action="store_true", help="List current conversation context")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (simulated GhidraMCP)")
    parser.add_argument("--log-level", help="Set log level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--include-capabilities", action="store_true", help="Include capabilities.txt content in prompts")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum number of steps for agentic execution loop")
    
    args = parser.parse_args()
    
    # Set log level from arguments or environment
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level
        
    # Configure based on arguments and environment variables
    config = BridgeConfig()
    
    # Override with command line arguments
    if args.ollama_url:
        config.ollama.base_url = args.ollama_url
    if args.ghidra_url:
        config.ghidra.base_url = args.ghidra_url
    if args.model:
        config.ollama.model = args.model
    if args.mock:
        config.ghidra.mock_mode = True
        
    # Handle model switching - update the model map
    if args.planning_model:
        config.ollama.model_map["planning"] = args.planning_model
    if args.execution_model:
        config.ollama.model_map["execution"] = args.execution_model
    if args.analysis_model:
        config.ollama.model_map["analysis"] = args.analysis_model
        
    # Initialize clients
    ollama_client = OllamaClient(config.ollama)
    ghidra_client = GhidraMCPClient(config.ghidra)
    
    # List models if requested
    if args.list_models:
        models = ollama_client.list_models()
        if models:
            print("Available Ollama models:")
            for model in models:
                print(f"  - {model}")
        else:
            print("No models found or error connecting to Ollama")
        return 0
    
    # Initialize the bridge
    bridge = Bridge(
        config=config,
        include_capabilities=args.include_capabilities,
        max_agent_steps=args.max_steps
    )
    
    # Health check for Ollama and GhidraMCP
    ollama_health = "OK" if ollama_client.check_health() else "FAIL"
    ghidra_health = "OK" if ghidra_client.check_health() else "FAIL"
    
    # List context if requested
    if args.list_context:
        print("\nCurrent conversation context:")
        for i, item in enumerate(bridge.context):
            print(f"{i}: {item.get('role', 'unknown')}: {item.get('content', '')[:50]}...")
        return 0
    
    # Interactive mode
    if args.interactive:
        # Display banner
        print(
            "╔══════════════════════════════════════════════════════════════════╗\n"
            "║                                                                  ║\n"
            "║  OGhidra - Simplified Three-Phase Architecture                   ║\n"
            "║  ------------------------------------------                      ║\n"
            "║                                                                  ║\n"
            "║  1. Planning Phase: Create a plan for addressing the query       ║\n"
            "║  2. Tool Calling Phase: Execute tools to gather information      ║\n"
            "║  3. Analysis Phase: Analyze results and provide answers          ║\n"
            "║                                                                  ║\n"
            "║  For more information, see README-ARCHITECTURE.md                ║\n"
            "║                                                                  ║\n"
            "╚══════════════════════════════════════════════════════════════════╝"
        )
        
        print(f"Ollama-GhidraMCP Bridge (Interactive Mode)")
        print(f"Default model: {config.ollama.model}")
        
        # Show health status
        if ollama_health != "OK" or ghidra_health != "OK":
            print(f"Health check: Ollama: {ollama_health}, GhidraMCP: {ghidra_health}")
        
        # Main interaction loop
        while True:
            try:
                prompt = input("\nQuery (or 'exit', 'quit', 'health', 'models'): ")
                
                if prompt.lower() in ["exit", "quit"]:
                    break
                    
                elif prompt.lower() == "health":
                    ollama_health = "OK" if ollama_client.check_health() else "FAIL"
                    ghidra_health = "OK" if ghidra_client.check_health() else "FAIL"
                    print(f"Health check: Ollama: {ollama_health}, GhidraMCP: {ghidra_health}")
                    
                elif prompt.lower() == "models":
                    models = ollama_client.list_models()
                    if models:
                        print("Available Ollama models:")
                        for model in models:
                            print(f"  - {model}")
                    else:
                        print("No models found or error connecting to Ollama")
                        
                elif prompt.strip():  # Only process non-empty prompts
                    response = bridge.process_query(prompt)
                    print(f"\n{response}")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
                
            except Exception as e:
                print(f"Error: {str(e)}")
                
        return 0
        
    # Non-interactive mode - process input from stdin
    else:
        user_input = ""
        for line in sys.stdin:
            user_input += line
            
        if user_input.strip():
            response = bridge.process_query(user_input)
            print(response)
            
        return 0

if __name__ == "__main__":
    main() 