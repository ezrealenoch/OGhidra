"""
Utility functions for working with Ghidra binary analysis results.

This module provides helper functions to parse and format data returned from
Ghidra tool calls, including function decompilation results, call graphs,
and other binary analysis artifacts.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

def parse_function_list(json_response: str) -> List[Dict[str, Any]]:
    """
    Parse the JSON response from ghidra_list_functions into a list of function objects.
    
    Args:
        json_response: The JSON string returned by ghidra_list_functions
        
    Returns:
        A list of dictionaries containing function information
        
    Raises:
        ValueError: If the JSON cannot be parsed or is not in the expected format
    """
    try:
        return json.loads(json_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse function list JSON: {e}")
        raise ValueError(f"Invalid JSON response from Ghidra: {e}")

def extract_function_names(functions: List[Dict[str, Any]]) -> List[str]:
    """
    Extract just the function names from a list of function objects.
    
    Args:
        functions: List of function dictionaries
        
    Returns:
        List of function names
    """
    return [func.get("name", "") for func in functions if func.get("name")]

def parse_called_functions(json_response: str) -> List[Dict[str, Any]]:
    """
    Parse the JSON response from ghidra_get_called_functions into a list of function objects.
    
    Args:
        json_response: The JSON string returned by ghidra_get_called_functions
        
    Returns:
        A list of dictionaries containing called function information
        
    Raises:
        ValueError: If the JSON cannot be parsed or is not in the expected format
    """
    try:
        return json.loads(json_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse called functions JSON: {e}")
        raise ValueError(f"Invalid JSON response from Ghidra: {e}")

def build_call_graph(function_name: str, called_functions_json: str) -> Dict[str, Any]:
    """
    Build a call graph starting from the specified function.
    
    Args:
        function_name: The name of the root function
        called_functions_json: JSON response from ghidra_get_called_functions
        
    Returns:
        A dictionary representing the call graph with the root function and its callees
    """
    called_functions = parse_called_functions(called_functions_json)
    
    # Create a simple call graph structure
    return {
        "function": function_name,
        "calls": extract_function_names(called_functions),
        "details": called_functions
    }

def recursive_call_graph(function_name: str, get_called_func_fn, depth: int = 3) -> Dict[str, Any]:
    """
    Build a recursive call graph starting from the specified function.
    
    Args:
        function_name: The name of the root function
        get_called_func_fn: Function that takes a function name and returns its called functions JSON
        depth: Maximum recursion depth
        
    Returns:
        A nested dictionary representing the recursive call graph
    """
    if depth <= 0:
        return {"function": function_name, "calls": ["..."], "details": []}
    
    try:
        called_functions_json = get_called_func_fn(function_name)
        called_functions = parse_called_functions(called_functions_json)
        
        # Create a call graph with recursive calls
        graph = {
            "function": function_name,
            "calls": extract_function_names(called_functions),
            "details": called_functions,
            "callees": {}
        }
        
        # Recursively get called functions for each callee
        for callee in extract_function_names(called_functions):
            graph["callees"][callee] = recursive_call_graph(
                callee, 
                get_called_func_fn, 
                depth - 1
            )
        
        return graph
    except Exception as e:
        logger.error(f"Error building recursive call graph for {function_name}: {e}")
        return {"function": function_name, "error": str(e)}

def format_function_summary(function_data: Dict[str, Any], decompiled_code: str) -> str:
    """
    Format a human-readable summary of a function based on its metadata and decompiled code.
    
    Args:
        function_data: Dictionary containing function metadata
        decompiled_code: The decompiled C code for the function
        
    Returns:
        A formatted string with function information
    """
    name = function_data.get("name", "unknown")
    address = function_data.get("address", "unknown")
    signature = function_data.get("signature", "unknown")
    description = function_data.get("description", "No description available")
    
    # Truncate decompiled code if too long
    if len(decompiled_code) > 1000:
        decompiled_code = decompiled_code[:997] + "..."
    
    summary = f"""
Function: {name}
Address: {address}
Signature: {signature}
Description: {description}

Decompiled Code:
{decompiled_code}
"""
    return summary

def extract_function_behaviors(decompiled_code: str) -> List[str]:
    """
    Extract key behaviors from decompiled function code.
    
    Args:
        decompiled_code: The decompiled C code for the function
        
    Returns:
        List of behavior descriptions
    """
    behaviors = []
    
    # Look for common patterns in the code
    if "malloc" in decompiled_code or "calloc" in decompiled_code:
        behaviors.append("Memory allocation")
    
    if "free" in decompiled_code:
        behaviors.append("Memory deallocation")
        
    if "fopen" in decompiled_code or "open(" in decompiled_code:
        behaviors.append("File operations")
        
    if "recv" in decompiled_code or "send" in decompiled_code:
        behaviors.append("Network operations")
        
    if "strcpy" in decompiled_code or "memcpy" in decompiled_code:
        behaviors.append("Memory copy operations")
        
    if "scanf" in decompiled_code or "gets" in decompiled_code:
        behaviors.append("User input handling")
    
    if "printf" in decompiled_code or "puts" in decompiled_code:
        behaviors.append("Output generation")
        
    if "strcmp" in decompiled_code or "memcmp" in decompiled_code:
        behaviors.append("Comparison operations")
        
    # Look for control flow patterns
    if "if" in decompiled_code and "return" in decompiled_code:
        behaviors.append("Conditional returns")
        
    if "for" in decompiled_code or "while" in decompiled_code:
        behaviors.append("Loop processing")
        
    if "switch" in decompiled_code:
        behaviors.append("Multiple branch decisions")
    
    return behaviors

def suggest_function_name(decompiled_code: str, old_name: str) -> str:
    """
    Suggest a new function name based on its behaviors.
    
    Args:
        decompiled_code: The decompiled C code for the function
        old_name: The current function name
        
    Returns:
        A suggested new function name
    """
    behaviors = extract_function_behaviors(decompiled_code)
    
    # If no behaviors detected, keep the old name
    if not behaviors:
        return old_name
    
    # Special cases based on common patterns
    if "Memory allocation" in behaviors and "File operations" in behaviors:
        return "read_file_into_memory"
        
    if "User input handling" in behaviors and "Comparison operations" in behaviors:
        return "validate_user_input"
        
    if "Network operations" in behaviors and "Memory copy operations" in behaviors:
        return "receive_network_data"
        
    if "Output generation" in behaviors and "Multiple branch decisions" in behaviors:
        return "display_status_message"
    
    # If no special case matches, use the primary behavior
    if behaviors:
        primary_behavior = behaviors[0].lower().replace(" ", "_")
        return f"{primary_behavior}_function"
    
    return old_name 