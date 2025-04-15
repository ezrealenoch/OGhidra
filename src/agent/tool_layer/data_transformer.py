"""
Data Transformation Module for Ghidra Tools
-------------------------------------------
This module handles transforming data received from the Ghidra server
into formats suitable for consumption by the Reasoning Layer's LLM.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("ollama-ghidra-bridge.agent.data_transformer")

class DataTransformer:
    """Transforms data between the Tool Layer and Reasoning Layer."""
    
    @staticmethod
    def format_function_list(functions: List[str]) -> str:
        """
        Format a list of functions for LLM consumption.
        
        Args:
            functions: List of function strings from Ghidra
            
        Returns:
            Formatted string representation of functions
        """
        if not functions:
            return "No functions found in the application."
            
        # Format as a readable list
        formatted = "Functions in the application:\n\n"
        for i, func in enumerate(functions, 1):
            formatted += f"{i}. {func}\n"
            
        return formatted
    
    @staticmethod
    def format_function_details(details: Dict[str, Any]) -> str:
        """
        Format function details for LLM consumption.
        
        Args:
            details: Dictionary of function details
            
        Returns:
            Formatted string representation of function details
        """
        if not details:
            return "No function details available."
            
        formatted = f"Function: {details.get('name', 'Unknown')}\n"
        formatted += f"Address: {details.get('address', 'Unknown')}\n\n"
        
        # Add decompiled code if available
        decompiled = details.get('decompiled_code')
        if decompiled:
            formatted += "Decompiled Code:\n"
            formatted += "```c\n"
            formatted += decompiled
            formatted += "\n```\n\n"
            
        # Add disassembly if available
        disassembly = details.get('disassembly')
        if disassembly and len(disassembly) > 0:
            formatted += "Disassembly:\n"
            formatted += "```asm\n"
            for line in disassembly[:50]:  # Limit to first 50 lines to avoid overwhelming the LLM
                formatted += line + "\n"
            if len(disassembly) > 50:
                formatted += f"[...] ({len(disassembly) - 50} more lines truncated)\n"
            formatted += "```\n"
            
        return formatted
    
    @staticmethod
    def format_memory_regions(regions: List[str]) -> str:
        """
        Format memory regions for LLM consumption.
        
        Args:
            regions: List of memory region strings from Ghidra
            
        Returns:
            Formatted string representation of memory regions
        """
        if not regions:
            return "No memory regions found in the application."
            
        formatted = "Memory Regions:\n\n"
        for i, region in enumerate(regions, 1):
            formatted += f"{i}. {region}\n"
            
        return formatted
    
    @staticmethod
    def format_imports(imports: List[str]) -> str:
        """
        Format imported symbols for LLM consumption.
        
        Args:
            imports: List of imported symbol strings from Ghidra
            
        Returns:
            Formatted string representation of imports
        """
        if not imports:
            return "No imports found in the application."
            
        formatted = "Imported Symbols:\n\n"
        for i, imp in enumerate(imports, 1):
            formatted += f"{i}. {imp}\n"
            
        return formatted
    
    @staticmethod
    def format_exports(exports: List[str]) -> str:
        """
        Format exported symbols for LLM consumption.
        
        Args:
            exports: List of exported symbol strings from Ghidra
            
        Returns:
            Formatted string representation of exports
        """
        if not exports:
            return "No exports found in the application."
            
        formatted = "Exported Symbols:\n\n"
        for i, exp in enumerate(exports, 1):
            formatted += f"{i}. {exp}\n"
            
        return formatted
    
    @staticmethod
    def format_search_results(results: List[str]) -> str:
        """
        Format search results for LLM consumption.
        
        Args:
            results: List of search result strings from Ghidra
            
        Returns:
            Formatted string representation of search results
        """
        if not results:
            return "No matches found for the search pattern."
            
        formatted = "Search Results:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result}\n"
            
        return formatted
    
    @staticmethod
    def format_command_result(command: str, result: Union[str, List[str], Dict[str, Any]]) -> str:
        """
        Format a command result for LLM consumption.
        
        Args:
            command: The command that was executed
            result: The result of the command execution
            
        Returns:
            Formatted string representation of the command result
        """
        formatted = f"Result of {command}:\n\n"
        
        if isinstance(result, str):
            formatted += result
        elif isinstance(result, list):
            for item in result:
                formatted += f"- {item}\n"
        elif isinstance(result, dict):
            formatted += json.dumps(result, indent=2)
        else:
            formatted += str(result)
            
        return formatted 