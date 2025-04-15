"""
CLI Handler for Agent Integration
-------------------------------
This module provides integration between the agent and the bridge's CLI interface.
"""

import logging
import argparse
from typing import Dict, Any, List, Optional

from src.config import BridgeConfig
from src.agent.agent_factory import AgentFactory

logger = logging.getLogger("ollama-ghidra-bridge.agent.cli_handler")

class AgentCLIHandler:
    """Handles CLI commands for the agent."""
    
    def __init__(self, config: BridgeConfig):
        """
        Initialize the CLI handler.
        
        Args:
            config: BridgeConfig instance
        """
        self.config = config
        self.agent = None
        logger.info("Initialized Agent CLI Handler")
        
    def setup_parser(self, subparsers) -> None:
        """
        Set up the CLI argument parser for agent commands.
        
        Args:
            subparsers: Subparsers object from argparse
        """
        agent_parser = subparsers.add_parser(
            "agent", 
            help="Run an autonomous agent to analyze application behavior"
        )
        
        agent_parser.add_argument(
            "--analyze",
            action="store_true",
            help="Analyze the current application's behavior"
        )
        
        agent_parser.add_argument(
            "--task",
            type=str,
            default="Analyze the behavior of the current application",
            help="Description of the analysis task"
        )
        
        agent_parser.add_argument(
            "--iterations",
            type=int,
            default=15,
            help="Maximum number of iterations for the agent (default: 15)"
        )
        
        agent_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print detailed progress information"
        )
        
        agent_parser.set_defaults(func=self.handle_command)
        
    def handle_command(self, args) -> int:
        """
        Handle agent CLI commands.
        
        Args:
            args: Parsed arguments from argparse
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        if args.analyze:
            return self.analyze_application(args.task, args.iterations, args.verbose)
        else:
            logger.error("No agent command specified")
            return 1
            
    def analyze_application(self, task_description: str, max_iterations: int, verbose: bool) -> int:
        """
        Analyze an application using the agent.
        
        Args:
            task_description: Description of the analysis task
            max_iterations: Maximum number of iterations
            verbose: Whether to print detailed progress information
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        logger.info(f"Starting application analysis with max_iterations={max_iterations}")
        logger.info(f"Task: {task_description}")
        
        try:
            # Create the agent
            self.agent = AgentFactory.create_agent(self.config, max_iterations=max_iterations)
            
            # Set up a progress observer if verbose output is requested
            if verbose:
                self.agent.register_observer(self._progress_print_observer)
                
            # Run the analysis
            analysis_result = self.agent.analyze_application(task_description)
            
            # Print the analysis result
            print("\n\n===== ANALYSIS RESULT =====\n")
            print(analysis_result)
            print("\n==========================\n")
            
            return 0
        except Exception as e:
            logger.error(f"Error during application analysis: {str(e)}")
            print(f"Error: {str(e)}")
            return 1
            
    def _progress_print_observer(self, step_type: str, step_name: str, details: str) -> None:
        """
        Observer function that prints progress information.
        
        Args:
            step_type: Type of step (thought, action, observation, analysis)
            step_name: Name of the step
            details: Details of the step
        """
        # Format the output based on step type
        if step_type == "thought":
            print(f"\n[AGENT THOUGHT] {step_name}")
            print(f"Reasoning: {details}")
        elif step_type == "action":
            print(f"\n[AGENT ACTION] {step_name}")
            print(f"Parameters: {details}")
        elif step_type == "observation":
            print(f"\n[AGENT OBSERVATION] {step_name}")
            print(f"Result: {details[:500]}...")  # Truncate long results
            if len(details) > 500:
                print(f"... (truncated {len(details) - 500} characters)")
        elif step_type == "analysis":
            print(f"\n[AGENT ANALYSIS] {step_name}")
            print(f"{details}")
        elif step_type == "error":
            print(f"\n[AGENT ERROR] {step_name}")
            print(f"Error: {details}")
        else:
            print(f"\n[AGENT {step_type.upper()}] {step_name}")
            print(f"{details}") 