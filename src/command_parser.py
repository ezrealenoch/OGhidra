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
            
            # Validate and transform parameters for specific commands
            params = CommandParser._validate_and_transform_params(command_name, params)
            
            commands.append((command_name, params))
            logger.debug(f"Extracted command: {command_name} with params: {params}")
            
        return commands
    
    @staticmethod
    def _validate_and_transform_params(command_name: str, params: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and potentially transform parameters for specific commands.
        This helps catch common errors before they reach the GhidraMCP client.
        
        Args:
            command_name: The name of the command
            params: The parsed parameters
            
        Returns:
            Validated and potentially transformed parameters
        """
        # Make a copy to avoid modifying the original
        validated_params = params.copy()
        
        # For rename_function_by_address, check if function_address is a function name
        if command_name == "rename_function_by_address" and "function_address" in validated_params:
            addr = validated_params["function_address"]
            
            # If it starts with "FUN_" and the rest is hex, extract just the hex part
            if addr.startswith("FUN_") and all(c in "0123456789abcdefABCDEF" for c in addr[4:]):
                # Extract just the address portion
                validated_params["function_address"] = addr[4:]
                logger.info(f"Transformed function address from '{addr}' to '{addr[4:]}'")
        
        # Handle 0x prefix in addresses for various functions
        address_param_names = ["address", "function_address"]
        for param_name in address_param_names:
            if param_name in validated_params:
                addr = validated_params[param_name]
                # If it starts with "0x", remove it
                if addr.startswith("0x") or addr.startswith("0X"):
                    validated_params[param_name] = addr[2:]
                    logger.info(f"Transformed address from '{addr}' to '{addr[2:]}'")
        
        return validated_params
    
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
    
    @staticmethod
    def remove_commands(text: str) -> str:
        """
        Remove EXECUTE command blocks from text to get the clean response.
        
        Args:
            text: The text containing EXECUTE blocks
            
        Returns:
            Clean text with EXECUTE blocks removed
        """
        # Simple pattern to remove EXECUTE: command() blocks
        clean_text = re.sub(r'EXECUTE:\s*[\w_]+\([^)]*\)', '', text)
        
        # Clean up any resulting double newlines
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)
        
        return clean_text.strip()
    
    @staticmethod
    def get_enhanced_error_message(command_name: str, params: Dict[str, str], error: str) -> str:
        """
        Generate an enhanced error message with specific guidance based on the command and error.
        
        Args:
            command_name: The command that was attempted
            params: The parameters that were used
            error: The original error message
            
        Returns:
            Enhanced error message with guidance
        """
        # Default to the original error
        enhanced_error = f"ERROR: {error}"
        
        # Add specific guidance based on the command and parameters
        if command_name == "rename_function_by_address":
            addr = params.get("function_address", "")
            if addr.startswith("FUN_"):
                return (
                    f"ERROR: Invalid parameter 'function_address'. Expected numerical address (e.g., '{addr[4:]}'), "
                    f"but received function name ('{addr}'). "
                    f"Use the correct address or the 'rename_function' tool if you only have the name."
                )
            elif "Failed to rename function" in error:
                return (
                    f"ERROR: Failed to rename function at address '{addr}'. "
                    f"This could be because the function doesn't exist at that address, "
                    f"or the new name is invalid or already in use. "
                    f"Try using get_function_by_address(address='{addr}') to verify the function exists."
                )
        elif command_name.startswith("decompile_"):
            return (
                f"ERROR: {error}. "
                f"The function may not exist or may not be a valid target for decompilation. "
                f"Try list_functions() to see available functions."
            )
            
        return enhanced_error 