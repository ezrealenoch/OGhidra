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
        
        # Context summarization settings
        self.context_summarization_threshold = self.config.context_limit * 0.8
        self.last_summarization_time = None
        
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

    def _build_structured_prompt(self, phase: str = None) -> str:
        """
        Build a structured prompt with clear sections for capabilities, history, current task,
        and phase-specific guidance.
        
        Args:
            phase: Optional phase name to customize the prompt
            
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
        
        # State information section - what the agent has already done
        state_section = ""
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
        plan_section = ""
        if self.current_plan:
            plan_section = f"## Current Plan:\n{self.current_plan}\n---\n\n"
            
        # Conversation history section
        history_items = []
        for item in self.context[-self.config.context_limit:]:
            prefix = "User: " if item["role"] == "user" else \
                    "Assistant: " if item["role"] == "assistant" else \
                    "Tool Call: " if item["role"] == "tool_call" else \
                    "Tool Result: " if item["role"] == "tool_result" else \
                    "AI Review: " if item["role"] == "review" else \
                    "Plan: " if item["role"] == "plan" else \
                    "Summary: " if item["role"] == "summary" else \
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
            "4. CRITICAL: You MUST use an explicit EXECUTE command for any action you want to perform. "
            "Simply stating that you 'will rename' or 'should add a comment' is NOT sufficient - you must "
            "include the actual EXECUTE command to perform the action.\n"
            "5. Provide analysis along with your tool calls\n"
            "6. Your response should be clear and concise\n"
            "7. When you have completed your analysis and are ready to provide a final answer, include \"FINAL RESPONSE:\" followed by your complete answer\n"
            "8. If you're unsure what to do or the request is ambiguous, ask a clarifying question instead of guessing\n"
            "9. If you identify useful combinations of tools for common tasks, you can make a `SUGGESTION:` for future improvements\n"
            "---\n\n"
        )
        
        # Add phase-specific sections
        if phase == "context_assessment":
            full_prompt = (
                "## Context Assessment Phase:\n"
                "Analyze the available information about the binary/program. Identify key areas of interest, "
                "complexity points, and potential challenges. Focus on building a high-level understanding.\n"
                "Please provide:\n"
                "1. An overview of what you can determine about the program\n"
                "2. Key areas that should be investigated\n"
                "3. Potential challenges in analysis\n"
                "4. Recommended approach based on available information\n"
            )
        elif phase == "tool_selection":
            full_prompt += (
                "## Tool Selection Phase:\n"
                "Based on the plan, identify the specific Ghidra tools needed to accomplish each step.\n"
                "For each planned step, specify:\n"
                "1. The exact tool command(s) that will be needed\n"
                "2. Any parameters or options that should be specified\n"
                "3. Alternative tools if the primary tool encounters issues\n"
            )
        
        # Create the full prompt
        full_prompt = capabilities_section + state_section + plan_section + history_section + instructions_section + full_prompt
        
        # Add final response request based on the last message
        if self.context and self.context[-1]["role"] == "user":
            if not self.current_plan:
                full_prompt += (
                    "## Planning Phase:\n"
                    "Before executing tools, create a detailed plan outlining the steps you'll take to address the user's request.\n"
                    "IMPORTANT: For any actions that modify content (like renaming functions or adding comments), you MUST explicitly "
                    "execute these commands using the EXECUTE: format. Simply suggesting or stating an intention to rename/modify "
                    "is not sufficient - you must output the actual command.\n"
                )
            else:
                full_prompt += "## Your Response:\n"
        elif self.context and self.context[-1]["role"] == "review":
            full_prompt += "## Continue Your Analysis:\nBased on the review feedback, continue your analysis or finalize your response.\n"
        elif self.context and self.context[-1]["role"] == "planning":
            full_prompt += "## Execute Plan:\nFollow the plan you created to address the user's request, executing tools as needed.\n"
            
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

    def _execute_single_command(self, command_name: str, params: Dict[str, Any]) -> str:
        """
        Execute a single GhidraMCP command with enhanced error handling and automatic recovery.
        
        Args:
            command_name: Name of the GhidraMCP command
            params: Command parameters
            
        Returns:
            Result or error string with suggestions
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
                    error_msg = self._handle_command_error(command_name, params, cmd_result.get("error", "Unknown error"))
                    return error_msg
                elif isinstance(cmd_result, str) and ("Failed" in cmd_result or "Error" in cmd_result):
                    error_msg = self._handle_command_error(command_name, params, cmd_result)
                    return error_msg
                else:
                    # Success! Update the analysis state
                    self._update_analysis_state(command_name, params, str(cmd_result))
                    
                    # Format the command result
                    if isinstance(cmd_result, (list, dict)):
                        formatted_result = f"RESULT: {json.dumps(cmd_result, indent=2)}"
                    else:
                        formatted_result = f"RESULT: {cmd_result}"
                    return formatted_result
            else:
                # Handle the case of an unknown command by providing alternative suggestions
                error_msg = f"ERROR: Unknown command '{command_name}'"
                self.logger.error(error_msg)
                
                # Suggest alternative commands based on similarity
                similar_commands = self._find_similar_commands(command_name)
                if similar_commands:
                    error_msg += f"\nDid you mean: {', '.join(similar_commands)}?"
                    
                # Check for common command patterns and suggest alternatives
                if command_name.startswith("search_"):
                    search_type = command_name[7:]  # Remove "search_" prefix
                    error_msg += f"\nTo search for {search_type}, try using search_functions_by_name with a relevant query."
                
                return error_msg
        except Exception as e:
            error_msg = self._handle_command_error(command_name, params, str(e))
            return error_msg
            
    def _find_similar_commands(self, unknown_command: str) -> List[str]:
        """
        Find similar commands to suggest when an unknown command is used.
        
        Args:
            unknown_command: The unknown command
            
        Returns:
            List of similar command suggestions
        """
        available_commands = [
            name for name in dir(self.ghidra) 
            if not name.startswith('_') and callable(getattr(self.ghidra, name))
        ]
        
        # Find commands with similar prefix or suffix
        similar_commands = []
        
        # Split the unknown command by underscores
        parts = unknown_command.split('_')
        
        for cmd in available_commands:
            # Check for commands with similar prefix
            if cmd.startswith(parts[0]) or unknown_command.startswith(cmd.split('_')[0]):
                similar_commands.append(cmd)
                continue
                
            # Check for commands with similar purpose
            if len(parts) > 1 and parts[-1] in cmd:
                similar_commands.append(cmd)
                
        return similar_commands[:3]  # Return top 3 similar commands

    def process_query(self, query: str) -> str:
        """
        Process a natural language query through the AI with an enhanced agentic loop.
        
        Args:
            query: The user's query
            
        Returns:
            The processed response with command results
        """
        # Check if this is a summarization task before starting
        is_summary_task = self._is_summarization_task(query)
        if is_summary_task:
            self.logger.info("Detected summarization/report task in query")
        
        # Add the query to context
        self.context.append({"role": "user", "content": query})
        
        # Check if we need to summarize context before processing
        if self._should_summarize_context():
            self._summarize_context()
        
        # Initialize state for this query
        self.current_plan = None
        self.planned_tools_tracker = {
            'planned': [], 'executed': [], 'pending_critical': []
        }
        final_response = ""
        self.partial_outputs = []
        
        # 1. Initial Context Assessment Phase
        # This phase analyzes available information and sets the scope
        context_assessment_result = self._run_context_assessment_phase()
        if self._check_for_clarification_request(context_assessment_result):
            return context_assessment_result
        
        # 2. Planning Phase - Now with context assessment information
        planning_result = self._run_planning_phase(context_assessment_result)
        if self._check_for_clarification_request(planning_result):
            return planning_result
        
        # 3. Tool Selection Phase - Identify tools needed for the task
        tool_selection_result = self._run_tool_selection_phase()
        if self._check_for_clarification_request(tool_selection_result):
            return tool_selection_result
        
        # 4. Primary Execution Loop - Execute tools with the selected models
        execution_result = self._run_execution_phase()
        if isinstance(execution_result, str) and execution_result:
            # If it's a clarification request or error
            return execution_result
        
        # 5. Verification Phase - Verify results against expectations
        verification_result = self._run_verification_phase()
        
        # 6. Review and Reasoning Phase - Evaluate completeness
        review_result = self._run_review_phase(verification_result)
        if isinstance(review_result, str) and review_result:
            final_response = review_result
        
        # 7. Learning/Adaptation Phase - Only run on successful completions
        if not tool_errors_encountered:
            self._run_learning_phase(final_response)
        
        return final_response
    
    def _run_context_assessment_phase(self) -> str:
        """Run the initial context assessment phase to analyze available information."""
        self.logger.info("Starting context assessment phase")
        
        # Build a prompt specifically for context assessment
        assessment_prompt = self._build_structured_prompt(phase="context_assessment")
        
        try:
            # Generate the context assessment using the specific model for this phase
            assessment_response = self.ollama.generate_for_phase(
                "context_assessment", assessment_prompt
            )
            self.logger.info(f"Received context assessment: {assessment_response[:100]}...")
            
            # Store the assessment in the context
            self.context.append({"role": "context_assessment", "content": assessment_response})
            
            # Store in partial outputs for reporting
            self.partial_outputs.append({
                "type": "context_assessment",
                "content": assessment_response,
                "phase": "context_assessment"
            })
            
            return assessment_response
        except Exception as e:
            error_msg = f"Error in context assessment phase: {str(e)}"
            self.logger.error(error_msg)
            return ""  # Return empty string to continue with planning phase

    def _run_planning_phase(self, context_assessment_result: str) -> str:
        """Run the planning phase with context assessment information."""
        self.logger.info("Starting planning phase")
        
        # Build a plan based on the context assessment result
        plan_text = f"Based on the context assessment, the plan is to: {context_assessment_result}"
        
        # Extract planned tools from the plan
        self._extract_planned_tools(plan_text)
        
        # Store the plan in the context and the state
        self.current_plan = plan_text
        self.context.append({"role": "plan", "content": plan_text})
        
        # Store planning phase output
        self.partial_outputs.append({
            "type": "planning", 
            "content": plan_text,
            "phase": "planning"
        })
        
        self.logger.info("Planning phase completed")
        
        return plan_text

    def _run_tool_selection_phase(self) -> str:
        """Run the tool selection phase to identify specific tools needed for the task."""
        self.logger.info("Starting tool selection phase")
        
        # Build a tool selection prompt
        tool_selection_prompt = self._build_structured_prompt(phase="tool_selection")
        
        try:
            # Get AI to select tools
            tool_selection_response = self.ollama.generate_for_phase(
                "tool_selection", tool_selection_prompt
            )
            self.logger.info(f"Received tool selection response: {tool_selection_response[:100]}...")
            
            # Extract tool suggestions
            tool_selection_response, suggestions = self._extract_suggestions(tool_selection_response)
            
            # Extract planned tools from the response
            self._extract_planned_tools(tool_selection_response)
            
            # Store the tool selection result in the context
            self.context.append({"role": "tool_selection", "content": tool_selection_response})
            
            self.logger.info("Tool selection phase completed")
            
            return tool_selection_response
        except Exception as e:
            error_msg = f"Error in tool selection phase: {str(e)}"
            self.logger.error(error_msg)
            return ""  # Return empty string to continue with execution phase

    def _run_execution_phase(self) -> str:
        """Run the execution phase to execute the selected tools."""
        self.logger.info("Starting execution phase")
        
        # Track if any errors were encountered during tool execution
        tool_errors_encountered = False
        unknown_commands_attempted = set()
        
        for step in range(self.max_agent_steps):
            # Check if we should summarize context
            if self._should_summarize_context():
                self._summarize_context()
                
            # Build the structured prompt with the current state and plan
            prompt = self._build_structured_prompt()
            
            # Send to Ollama
            self.logger.info(f"Step {step+1}/{self.max_agent_steps}: Sending query to Ollama")
            
            try:
                # Get AI response
                ai_response = self.ollama.generate_for_phase(
                    "execution", prompt
                )
                self.logger.info(f"Received response from Ollama: {ai_response[:100]}...")
                
                # Capture the full response as logged
                self.partial_outputs.append({
                    "type": "raw_response",
                    "content": ai_response,
                    "step": step + 1
                })
                
                # Check if this is a clarification request
                if self._check_for_clarification_request(ai_response):
                    self.logger.info("AI is requesting clarification from user")
                    return ai_response  # Return the question directly to the user
                    
                # Extract any tool suggestions
                ai_response, suggestions = self._extract_suggestions(ai_response)
                
                # Parse commands from the response
                commands = CommandParser.extract_commands(ai_response)
                
                # Clean the response text (remove EXECUTE blocks)
                clean_response = self._remove_commands(ai_response)
                
                # Add the clean response to context
                if clean_response.strip():
                    self.context.append({"role": "assistant", "content": clean_response.strip()})
                    final_response = clean_response.strip()
                    # Store the assistant's reasoning as a partial output
                    self.partial_outputs.append({
                        "type": "reasoning",
                        "content": clean_response.strip(),
                        "step": step + 1
                    })
                
                # If no commands found, we're done with the tool execution phase
                if not commands:
                    self.logger.info("No commands found in AI response, ending tool execution loop")
                    break
                
                # Execute each command and add to context
                all_results = []
                step_errors = False
                
                for cmd_name, cmd_params in commands:
                    # Add tool call to context
                    params_str = ", ".join([f"{k}=\"{v}\"" for k, v in cmd_params.items()])
                    tool_call = f"EXECUTE: {cmd_name}({params_str})"
                    self.context.append({"role": "tool_call", "content": tool_call})
                    
                    # Execute the command
                    result = self._execute_single_command(cmd_name, cmd_params)
                    all_results.append((tool_call, result))
                    
                    # Update planned tools tracker
                    self._mark_tool_as_executed(cmd_name, cmd_params)
                    
                    # Check if this was an error and track unknown commands
                    if "ERROR: Unknown command" in result:
                        unknown_commands_attempted.add(cmd_name)
                        step_errors = True
                        tool_errors_encountered = True
                    elif "ERROR:" in result or "Failed" in result:
                        step_errors = True
                        tool_errors_encountered = True
                    
                    # Add result to context
                    self.context.append({"role": "tool_result", "content": result})
                    
                    # Store the tool result as a partial output
                    self.partial_outputs.append({
                        "type": "tool_result",
                        "tool": cmd_name,
                        "params": cmd_params,
                        "result": result,
                        "step": step + 1
                    })
                
                # Update final response with results
                final_response = clean_response + "\n\n" + "\n".join([result for _, result in all_results])
                
                # Check if any command failed - if so, let the AI try again in the next step
                if not step_errors:
                    # If all commands succeeded, we can break the loop
                    self.logger.info("All commands executed successfully, ending tool execution loop")
                    break
                
            except Exception as e:
                error_msg = f"Error in agent step {step+1}: {str(e)}"
                self.logger.error(error_msg)
                final_response = f"Sorry, I encountered an error: {str(e)}"
                tool_errors_encountered = True
                break
        
        # 3. Secondary review and reasoning loop - evaluates completeness of response
        self.logger.info("Starting review and reasoning phase")
        review_step = 0
        has_final_response = False
        
        while review_step < self.max_review_rounds and not has_final_response:
            # Check if we should summarize context
            if self._should_summarize_context():
                self._summarize_context()
                
            # Check if current final_response already contains "FINAL RESPONSE"
            if "FINAL RESPONSE:" in final_response:
                # Extract the part after "FINAL RESPONSE:"
                final_parts = final_response.split("FINAL RESPONSE:", 1)
                potential_final = ""
                if len(final_parts) > 1:
                    potential_final = final_parts[1].strip()
                
                # Check for implied actions without commands
                implied_actions_prompt = self._check_implied_actions_without_commands(final_response)
                if implied_actions_prompt:
                    self.logger.info("Found implied actions without commands in final response")
                    # Add a prompt for the next round asking for explicit commands
                    self.context.append({"role": "review", "content": implied_actions_prompt})
                    continue  # Skip to next review round
                
                # Check the quality of the final response
                if self._check_final_response_quality(potential_final):
                    has_final_response = True
                    self.logger.info("Found high-quality 'FINAL RESPONSE' marker, ending review loop")
                    final_response = potential_final
                    break
                else:
                    # If the final response indicates limitations, continue with more review steps
                    self.logger.info("Found 'FINAL RESPONSE' marker but response indicates limitations, continuing review")
                    # If tool errors were encountered, mention them explicitly in the prompt
                    if tool_errors_encountered:
                        review_prompt = (
                            f"Some tool errors or missing commands were encountered during execution. "
                            f"Based on the available information so far, please provide the most complete analysis possible "
                            f"using only the tools that worked successfully. "
                            f"If you've completed your analysis with available tools, provide a final answer prefixed with 'FINAL RESPONSE:'"
                        )
                        if unknown_commands_attempted:
                            cmd_list = ", ".join(f"'{cmd}'" for cmd in unknown_commands_attempted)
                            review_prompt += f"\n\nNote: These commands are not available: {cmd_list}. Use alternatives."
                    else:
                        review_prompt = (
                            f"Your previous final response indicated some limitations. Please review your analysis again "
                            f"and see if you can overcome these limitations with alternative approaches. "
                            f"If you've completed your analysis, provide a final answer prefixed with 'FINAL RESPONSE:'"
                        )
                    
                    # Add information about pending critical tools
                    pending_tools_prompt = self._get_pending_critical_tools_prompt()
                    if pending_tools_prompt:
                        review_prompt += pending_tools_prompt
                        
                    self.context.append({"role": "review", "content": review_prompt})
            else:
                # Regular review prompt
                review_prompt = (
                    f"Review your analysis so far. Have you completed the task? "
                    f"If not, what additional information or analysis is needed? "
                    f"If yes, provide a complete and comprehensive final answer prefixed with 'FINAL RESPONSE:'"
                )
                
                # Add information about pending critical tools
                pending_tools_prompt = self._get_pending_critical_tools_prompt()
                if pending_tools_prompt:
                    review_prompt += pending_tools_prompt
                    
                self.context.append({"role": "review", "content": review_prompt})
            
            # Build a new prompt with the review context
            prompt = self._build_structured_prompt()
            
            # Send to Ollama for review
            self.logger.info(f"Review step {review_step+1}/{self.max_review_rounds}: Asking AI to review response")
            
            try:
                # Get AI's review response
                ai_review_response = self.ollama.generate_for_phase(
                    "review", prompt
                )
                self.logger.info(f"Received review response: {ai_review_response[:100]}...")
                
                # Capture the full review response as logged
                self.partial_outputs.append({
                    "type": "raw_review",
                    "content": ai_review_response,
                    "review_step": review_step + 1
                })
                
                # Check if this is a clarification request
                if self._check_for_clarification_request(ai_review_response):
                    self.logger.info("AI is requesting clarification from user during review")
                    return ai_review_response  # Return the question directly to the user
                    
                # Extract any tool suggestions
                ai_review_response, suggestions = self._extract_suggestions(ai_review_response)
                
                # Clean the response and update
                clean_review = self._remove_commands(ai_review_response)
                if clean_review.strip():
                    self.context.append({"role": "assistant", "content": clean_review.strip()})
                    final_response = clean_review.strip()
                    
                    # Store the review reasoning as a partial output
                    self.partial_outputs.append({
                        "type": "review",
                        "content": clean_review.strip(),
                        "review_step": review_step + 1
                    })
                    
                    # Check if this response has the final marker
                    if "FINAL RESPONSE:" in clean_review:
                        # Extract the part after "FINAL RESPONSE:"
                        final_parts = clean_review.split("FINAL RESPONSE:", 1)
                        potential_final = ""
                        if len(final_parts) > 1:
                            potential_final = final_parts[1].strip()
                        
                        # Check for implied actions without commands
                        implied_actions_prompt = self._check_implied_actions_without_commands(clean_review)
                        if implied_actions_prompt:
                            self.logger.info("Found implied actions without commands in review response")
                            # Add a prompt for the next round asking for explicit commands
                            self.context.append({"role": "review", "content": implied_actions_prompt})
                            continue  # Skip to next review round
                        
                        # Check the quality of the final response
                        if self._check_final_response_quality(potential_final):
                            has_final_response = True
                            self.logger.info("Found high-quality 'FINAL RESPONSE' marker in review, ending review loop")
                            final_response = potential_final
                            break
                        else:
                            # If tool errors were encountered and we're near the end of review rounds, accept the response anyway
                            if tool_errors_encountered and review_step >= self.max_review_rounds - 2:
                                has_final_response = True
                                self.logger.info("Accepting final response despite limitations due to tool errors")
                                final_response = potential_final
                                break
                            else:
                                self.logger.info("Found 'FINAL RESPONSE' marker but response indicates limitations, continuing review")
                
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
                        
                        # Update planned tools tracker
                        self._mark_tool_as_executed(cmd_name, cmd_params)
                        
                        # Check if this was an error and track unknown commands
                        if "ERROR: Unknown command" in result:
                            unknown_commands_attempted.add(cmd_name)
                            tool_errors_encountered = True
                        
                        # Store the tool result from review as a partial output
                        self.partial_outputs.append({
                            "type": "review_tool_result",
                            "tool": cmd_name,
                            "params": cmd_params,
                            "result": result,
                            "review_step": review_step + 1
                        })
            
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
            
            # Generate a cohesive report from partial outputs if no final response marker was found
            final_response = self._generate_cohesive_report()
            
        return final_response
    
    def _run_verification_phase(self, execution_result: str) -> str:
        """Run the verification phase to verify results against expectations."""
        self.logger.info("Starting verification phase")
        
        # Build a verification prompt
        verification_prompt = self._build_structured_prompt(phase="verification")
        
        try:
            # Get AI to verify the results
            verification_response = self.ollama.generate_for_phase(
                "verification", verification_prompt
            )
            self.logger.info(f"Received verification response: {verification_response[:100]}...")
            
            # Store the verification result in the context
            self.context.append({"role": "verification", "content": verification_response})
            
            # Store in partial outputs for reporting
            self.partial_outputs.append({
                "type": "verification",
                "content": verification_response,
                "phase": "verification"
            })
            
            return verification_response
        except Exception as e:
            error_msg = f"Error in verification phase: {str(e)}"
            self.logger.error(error_msg)
            return ""  # Return empty string to continue with learning phase

    def _run_learning_phase(self, final_response: str) -> None:
        """Run the learning phase to extract patterns and update knowledge for future use."""
        self.logger.info("Starting learning phase")
        
        # Build a learning prompt
        learning_prompt = self._build_structured_prompt(phase="learning")
        
        try:
            # Get AI to learn from the final response
            learning_response = self.ollama.generate_for_phase(
                "learning", learning_prompt
            )
            self.logger.info(f"Received learning response: {learning_response[:100]}...")
            
            # Store the learning result in the context
            self.context.append({"role": "learning", "content": learning_response})
            
            # Store in partial outputs for reporting
            self.partial_outputs.append({
                "type": "learning",
                "content": learning_response,
                "phase": "learning"
            })
            
            # Update analysis state based on the learning response
            self._update_analysis_state_from_learning(learning_response)
        except Exception as e:
            error_msg = f"Error in learning phase: {str(e)}"
            self.logger.error(error_msg)

    def _update_analysis_state_from_learning(self, learning_response: str) -> None:
        """Update the internal analysis state based on the learning response."""
        # Implement the logic to update the analysis state based on the learning response
        # This is a placeholder and should be replaced with the actual implementation
        pass

    def _remove_commands(self, text: str) -> str:
        """
        Remove EXECUTE command blocks from text to get the clean response.
        
        Args:
            text: The text containing EXECUTE blocks
            
        Returns:
            Clean text with EXECUTE blocks removed
        """
        return CommandParser.remove_commands(text)
    
    def _handle_command_error(self, command_name: str, params: Dict[str, Any], error_message: str) -> str:
        """
        Handle command errors with recovery actions and enhanced error messages.
        
        Args:
            command_name: The command that was executed
            params: The parameters that were used
            error_message: The original error message
            
        Returns:
            Enhanced error message with recovery suggestions
        """
        self.logger.error(f"Error executing {command_name}: {error_message}")
        
        # Attempt recovery action based on the command and error
        recovery_result = None
        recovery_performed = False
        suggestion = ""
        
        # Function not found errors
        if "not found" in error_message.lower() or "does not exist" in error_message.lower():
            if command_name in ["rename_function_by_address", "decompile_function_by_address", "disassemble_function"]:
                # Try to get a list of functions to verify if the address exists
                self.logger.info(f"Attempting recovery by listing available functions")
                try:
                    functions = self.ghidra.list_functions()
                    if isinstance(functions, list) and functions:
                        recovery_result = f"Available functions (sample): {', '.join(functions[:10])}"
                        recovery_performed = True
                        suggestion = "Use list_functions() to see all available functions and verify addresses."
                except Exception as e:
                    self.logger.error(f"Recovery attempt failed: {str(e)}")
                    
        # Address format errors
        if "address" in error_message.lower() and "invalid" in error_message.lower():
            if "function_address" in params:
                # Attempt to format the address correctly
                addr = params.get("function_address", "")
                if addr.startswith("FUN_"):
                    suggestion = f"Function addresses should not include 'FUN_' prefix. Try '{addr[4:]}' instead."
                elif not addr.startswith("0x") and all(c in "0123456789abcdefABCDEF" for c in addr):
                    suggestion = f"Try formatting the address with '0x' prefix: '0x{addr}'"
                    
        # Network or connection errors
        if "connection" in error_message.lower() or "timeout" in error_message.lower():
            suggestion = "Check if Ghidra and the GhidraMCP server are running and accessible."
            
        # Get enhanced error from CommandParser
        enhanced_error = CommandParser.get_enhanced_error_message(command_name, params, error_message)
        
        # Build the final error message
        final_error = enhanced_error
        if recovery_performed and recovery_result:
            final_error += f"\n\nRecovery information: {recovery_result}"
        if suggestion:
            final_error += f"\n\nSuggestion: {suggestion}"
            
        return final_error
    
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

    def _should_summarize_context(self) -> bool:
        """
        Determine if the context should be summarized based on length.
        
        Returns:
            True if context should be summarized, False otherwise
        """
        return len(self.context) >= self.context_summarization_threshold
    
    def _summarize_context(self) -> None:
        """
        Summarize the conversation context to preserve key information while reducing length.
        Uses the specialized summarization model if configured.
        """
        if len(self.context) <= 5:  # Don't summarize very short contexts
            return
            
        # Create a prompt for the LLM to summarize the context
        summarization_instruction = (
            "Summarize the key points, findings, and outstanding tasks from this conversation history. "
            "Preserve important technical details, especially addresses and function names. "
            "Format the summary in bullet points with the most important information first."
        )
        
        # Build a prompt with just the context to summarize
        context_items = []
        # Get items except the last few (keep recent items unsummarized)
        items_to_summarize = self.context[:-5]
        for item in items_to_summarize:
            prefix = "User: " if item["role"] == "user" else \
                    "Assistant: " if item["role"] == "assistant" else \
                    "Tool Call: " if item["role"] == "tool_call" else \
                    "Tool Result: " if item["role"] == "tool_result" else \
                    "AI Review: " if item["role"] == "review" else \
                    "Plan: " if item["role"] == "plan" else \
                    "Summary: " if item["role"] == "summary" else \
                    f"{item['role'].capitalize()}: "
            context_items.append(f"{prefix}{item['content']}")
        
        context_text = "\n".join(context_items)
        summarization_prompt = f"{context_text}\n\n{summarization_instruction}"
        
        try:
            # Ask the LLM to summarize using the specialized model
            self.logger.info("Summarizing conversation context")
            summary = self.ollama.generate_with_summarization_model(
                summarization_prompt, 
                "You are a helpful assistant tasked with summarizing technical conversations about reverse engineering."
            )
            
            # Replace the old context items with the new summary
            # Keep all special entries (plans, etc.) but remove regular conversation
            kept_items = [item for item in self.context[-5:]]  # Keep the most recent items
            special_items = [item for item in items_to_summarize if item["role"] not in ["user", "assistant", "tool_call", "tool_result"]]
            
            # Create a new context with the summary as the first item
            new_context = [{"role": "summary", "content": summary}]
            new_context.extend(special_items)
            new_context.extend(kept_items)
            
            self.context = new_context
            self.logger.info(f"Context summarized, reduced from {len(items_to_summarize) + 5} to {len(new_context)} items")
            
        except Exception as e:
            self.logger.error(f"Error summarizing context: {str(e)}")
            # If summarization fails, fall back to simple truncation
            self.context = self.context[-self.config.context_limit:]
            
    def _update_analysis_state(self, command_name: str, params: Dict[str, Any], result: str) -> None:
        """
        Update the internal analysis state based on the executed command and result.
        
        Args:
            command_name: The command that was executed
            params: The parameters that were used
            result: The result of the command
        """
        # Only update state if command was successful
        if "ERROR" in result or "Failed" in result:
            return
            
        # Track decompiled functions
        if command_name == "decompile_function" and "name" in params:
            self.analysis_state["functions_analyzed"].add(params["name"])
            
        elif command_name == "decompile_function_by_address" and "address" in params:
            address = params["address"]
            self.analysis_state["functions_decompiled"].add(address)
            self.analysis_state["functions_analyzed"].add(address)
            
        # Track renamed functions
        elif command_name == "rename_function" and "old_name" in params and "new_name" in params:
            self.analysis_state["functions_renamed"][params["old_name"]] = params["new_name"]
            
        elif command_name == "rename_function_by_address" and "function_address" in params and "new_name" in params:
            self.analysis_state["functions_renamed"][params["function_address"]] = params["new_name"]
            
        # Track comments added
        elif command_name in ["set_decompiler_comment", "set_disassembly_comment"] and "address" in params and "comment" in params:
            self.analysis_state["comments_added"][params["address"]] = params["comment"]
    
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
        Generate a cohesive report from partial outputs collected during the agentic process.
        This combines all reasoning steps, planning, tool results, and errors into a structured report.
        Uses a specialized summarization model if configured.
        
        Returns:
            A cohesive report combining all partial outputs
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
        
        # Option 2: Use a specialized summarization model to generate the report
        if self.config.ollama.summarization_model:
            try:
                # Prepare the input for the summarization model by converting our report_sections to text
                summarization_input = self._prepare_summarization_input(report_sections)
                
                self.logger.info("Generating comprehensive report using specialized summarization model")
                ai_generated_report = self.ollama.generate_with_summarization_model(summarization_input)
                
                # If the AI-generated report is too short or empty, fall back to our structured report
                if len(ai_generated_report.strip()) < 100:
                    self.logger.warning("AI-generated report was too short, using structured report instead")
                    return report
                
                return ai_generated_report
            except Exception as e:
                self.logger.error(f"Error generating report with summarization model: {str(e)}")
                # Fall back to structured report on error
                return report
        
        # Return the manually structured report if no specialized model
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
    
    def _prepare_summarization_input(self, report_sections):
        """
        Prepare the input for the summarization model by converting our report sections to text.
        
        Args:
            report_sections: Dict of report sections
            
        Returns:
            A formatted string to send to the summarization model
        """
        input_parts = []
        
        input_parts.append("# Analysis Information\n")
        input_parts.append("Please generate a comprehensive analysis report based on the following information:\n")
        
        if report_sections["plan"]:
            input_parts.append("\n## Initial Plan:\n")
            for plan in report_sections["plan"]:
                input_parts.append(plan)
        
        if report_sections["insights"]:
            input_parts.append("\n## Key Insights Found:\n")
            for idx, insight in enumerate(report_sections["insights"], 1):
                input_parts.append(f"{idx}. {insight}")
        
        if report_sections["findings"]:
            input_parts.append("\n## Findings:\n")
            for finding in report_sections["findings"]:
                input_parts.append(f"- {finding}")
        
        if report_sections["analysis"]:
            input_parts.append("\n## Technical Analysis Details:\n")
            for analysis in report_sections["analysis"]:
                input_parts.append(analysis + "\n")
        
        if report_sections["tools"]:
            input_parts.append("\n## Tools Used:\n")
            for tool in report_sections["tools"]:
                input_parts.append(f"- {tool}")
        
        if report_sections["errors"]:
            input_parts.append("\n## Errors Encountered:\n")
            for error in report_sections["errors"]:
                input_parts.append(f"- {error}")
        
        if report_sections["conclusions"]:
            input_parts.append("\n## Preliminary Conclusions:\n")
            for conclusion in report_sections["conclusions"]:
                input_parts.append(conclusion)
                
        input_parts.append("\n# Report Format Request:\n")
        input_parts.append("Please organize this information into a well-structured analysis report with clear sections.")
        input_parts.append("Include an executive summary at the beginning and a conclusion at the end.")
        input_parts.append("Format your response using Markdown, with appropriate headers, bullet points, and emphasis.")
        
        return "\n".join(input_parts)

    def _is_summarization_task(self, query: str) -> bool:
        """
        Detect if the query is asking for a summarization or report.
        
        Args:
            query: The user's query
            
        Returns:
            True if the query appears to be requesting a summary or report
        """
        # Look for keywords that indicate a summarization task
        summarization_keywords = [
            "summarize", "summarization", "summary",
            "report", "overview", 
            "analyze the results", "final analysis",
            "produce a report", "generate a report",
            "compile", "findings", "conclude",
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in summarization_keywords)

    def _extract_planned_tools(self, plan_text: str) -> None:
        """
        Extract planned tool calls from the AI's planning response.
        Identifies which tools the AI plans to use and marks critical ones.
        
        Args:
            plan_text: The AI's planning response text
        """
        # Reset the planned tools tracker for the new plan
        self.planned_tools_tracker = {
            'planned': [],
            'executed': [],
            'pending_critical': []
        }
        
        # Common tools that might be mentioned in plans
        common_tools = [
            "list_functions", "list_methods", "decompile_function", "decompile_function_by_address",
            "rename_function", "rename_function_by_address", "set_decompiler_comment", 
            "set_disassembly_comment", "search_functions_by_name", "disassemble_function"
        ]
        
        # Patterns that indicate a tool is critical to the task
        critical_patterns = [
            "will need to", "essential", "necessary", "required", "important", 
            "critical", "key step", "must", "rename", "need to"
        ]
        
        # Process each line of the plan
        lines = plan_text.lower().split('\n')
        for i, line in enumerate(lines):
            # Check for mentions of tools in this line
            for tool in common_tools:
                if tool.lower() in line:
                    # Check if this is part of a numbered or bulleted step
                    is_step = bool(re.match(r'^\s*(\d+\.|[\-\*•])', line))
                    
                    # Look at surrounding context (current line and next line if available)
                    context = line
                    if i < len(lines) - 1:
                        context += " " + lines[i + 1]
                    
                    # Determine if this tool is critical based on context
                    is_critical = False
                    for pattern in critical_patterns:
                        if pattern in context:
                            is_critical = True
                            break
                    
                    # Create a tool tracking entry
                    tool_entry = {
                        'tool': tool,
                        'execution_status': 'pending',
                        'is_critical': is_critical or 'rename' in tool,  # Always mark rename operations as critical
                        'context': context
                    }
                    
                    self.planned_tools_tracker['planned'].append(tool_entry)
                    
                    # Add critical tools to the pending critical list
                    if tool_entry['is_critical']:
                        self.planned_tools_tracker['pending_critical'].append(tool_entry)
                        
        self.logger.info(f"Extracted {len(self.planned_tools_tracker['planned'])} planned tools from plan")
        if self.planned_tools_tracker['pending_critical']:
            self.logger.info(f"Identified {len(self.planned_tools_tracker['pending_critical'])} critical tools in plan")

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

def main():
    """Main entry point for the bridge application."""
    parser = argparse.ArgumentParser(description="Ollama-GhidraMCP Bridge")
    parser.add_argument("--ollama-url", help="Ollama server URL")
    parser.add_argument("--ghidra-url", help="GhidraMCP server URL")
    parser.add_argument("--model", help="Ollama model to use")
    parser.add_argument("--summarization-model", help="Specialized model to use for summarization and report generation (defaults to main model if not specified)")
    
    # Add model arguments for each phase
    parser.add_argument("--planning-model", help="Model to use for the planning phase")
    parser.add_argument("--execution-model", help="Model to use for the execution phase")
    parser.add_argument("--review-model", help="Model to use for the review phase")
    parser.add_argument("--verification-model", help="Model to use for the verification phase")
    parser.add_argument("--learning-model", help="Model to use for the learning phase")
    
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--health-check", action="store_true", help="Check health of services and exit")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no GhidraMCP server needed)")
    parser.add_argument("--include-capabilities", action="store_true", 
                        help="Include capabilities context from ai_ghidra_capabilities.txt in prompts")
    parser.add_argument("--max-steps", type=int, default=5, 
                        help="Maximum number of steps for agentic execution loop (default: 5)")
    parser.add_argument("--max-review-rounds", type=int, default=3,
                        help="Maximum number of review rounds after tool execution (default: 3)")
    parser.add_argument("--list-models", action="store_true", 
                        help="List available models from Ollama server and exit")
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
    if args.summarization_model:
        config.ollama.summarization_model = args.summarization_model
    if args.mock:
        config.ghidra.mock_mode = True
        print("Running in MOCK mode - No GhidraMCP server required")
    
    # Set up model map from command-line arguments
    model_map = {}
    phase_models = [
        ("planning", args.planning_model),
        ("execution", args.execution_model),
        ("review", args.review_model),
        ("verification", args.verification_model),
        ("learning", args.learning_model),
        # Summarization uses the summarization_model parameter
    ]
    
    for phase, model in phase_models:
        if model:
            model_map[phase] = model
    
    # Only update if at least one model was specified
    if model_map:
        config.ollama.model_map.update(model_map)
    
    # Pass the flag to the Bridge constructor
    bridge = Bridge(
        config, 
        include_capabilities=args.include_capabilities,
        max_agent_steps=args.max_steps,
        max_review_rounds=args.max_review_rounds
    )
    
    # List models and exit if requested
    if args.list_models:
        try:
            models = bridge.ollama.list_models()
            print("Available Ollama models:")
            for model in models:
                print(f"- {model}")
            sys.exit(0)
        except Exception as e:
            print(f"Error listing models: {str(e)}")
            sys.exit(1)
    
    if args.health_check:
        status = bridge.health_check()
        print(f"Ollama Health: {'OK' if status['ollama'] else 'FAIL'}")
        print(f"GhidraMCP Health: {'OK' if status['ghidra'] else 'FAIL'}")
        sys.exit(0 if all(status.values()) else 1)
    
    if args.interactive:
        print("Ollama-GhidraMCP Bridge (Interactive Mode)")
        print(f"Default model: {config.ollama.model}")
        
        # Print phase-specific models if configured
        for phase, model in config.ollama.model_map.items():
            if model:
                print(f"Model for {phase} phase: {model}")
                
        if config.ollama.summarization_model:
            print(f"Model for summarization: {config.ollama.summarization_model}")
            
        print(f"Capabilities included: {'Yes' if args.include_capabilities else 'No'}")
        print(f"Tool execution steps: {bridge.max_agent_steps}")
        print(f"Review rounds: {bridge.max_review_rounds}")
        print("Type 'exit' or 'quit' to exit, 'models' to list available models")
        
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
                    
                if query.lower() == "models":
                    try:
                        models = bridge.ollama.list_models()
                        print("\nAvailable Ollama models:")
                        for model in models:
                            print(f"- {model}")
                    except Exception as e:
                        print(f"Error listing models: {str(e)}")
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