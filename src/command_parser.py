"""
Command parser module for extracting and executing GhidraMCP commands from AI responses.
"""

import json
import logging
import re
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("ollama-ghidra-bridge.parser")

class CommandParser:
    """
    Parser for extracting and validating commands from AI responses.
    """
    
    # Command format: EXECUTE: command_name(param1=value1, param2=value2)
    COMMAND_PATTERN = r'EXECUTE:\s*([\w_]+)\((.*?)\)'
    
    @staticmethod
    def extract_commands(response: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        Extract commands and their parameters from an AI response.
        
        Args:
            response: The AI's response text
            
        Returns:
            List of tuples containing (command_name, parameters_dict)
        """
        commands = []
        
        # Find all command occurrences in the response
        matches = re.finditer(CommandParser.COMMAND_PATTERN, response, re.MULTILINE)
        
        for match in matches:
            command_name = match.group(1)
            params_text = match.group(2).strip()
            
            # Parse parameters
            params = CommandParser._parse_parameters(params_text)
            
            commands.append((command_name, params))
            logger.debug(f"Extracted command: {command_name} with params: {params}")
            
        return commands
    
    @staticmethod
    def _parse_parameters(params_text: str) -> Dict[str, str]:
        """
        Parse parameters from the parameter text string.
        
        Args:
            params_text: The parameter text (e.g. 'param1="value1", param2="value2"')
            
        Returns:
            Dictionary of parameter names to values
        """
        params = {}
        
        if not params_text:
            return params
            
        # Split by commas, but not within quotes
        param_list = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in params_text:
            if char in ('"', "'") and (not in_quotes or quote_char == char):
                in_quotes = not in_quotes
                if in_quotes:
                    quote_char = char
                else:
                    quote_char = None
                current += char
            elif char == ',' and not in_quotes:
                param_list.append(current.strip())
                current = ""
            else:
                current += char
                
        if current:
            param_list.append(current.strip())
            
        # Process each parameter
        for param in param_list:
            if '=' in param:
                key, value = param.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                    
                params[key] = value
        
        return params
    
    @staticmethod
    def format_command_results(command: str, params: Dict[str, str], result: Dict[str, Any]) -> str:
        """
        Format the results of a command execution.
        
        Args:
            command: The command that was executed
            params: The parameters that were used
            result: The result dictionary from the command execution
            
        Returns:
            Formatted string representation of the results
        """
        formatted_result = f"Results of {command}:\n"
        formatted_result += json.dumps(result, indent=2)
        return formatted_result
    
    @staticmethod
    def replace_command_with_result(response: str, cmd_match: re.Match, result: str) -> str:
        """
        Replace a command in the response with its execution result.
        
        Args:
            response: The original AI response
            cmd_match: The regex match object for the command
            result: The formatted result string
            
        Returns:
            The response with the command replaced by its result
        """
        start, end = cmd_match.span()
        return response[:start] + result + response[end:] 