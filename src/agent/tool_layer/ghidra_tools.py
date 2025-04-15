"""
Tool Layer for Ghidra Interaction
---------------------------------
This module abstracts the Ghidra server functionalities into tools 
that can be used by the Reasoning Layer.
"""

import logging
from typing import Dict, Any, List, Optional

from src.ghidra_client import GhidraMCPClient

logger = logging.getLogger("ollama-ghidra-bridge.agent.tool_layer")

class GhidraTools:
    """Tools for interacting with Ghidra server via GhidraMCPClient."""
    
    def __init__(self, ghidra_client: GhidraMCPClient):
        """
        Initialize the Ghidra tools.
        
        Args:
            ghidra_client: GhidraMCPClient instance for Ghidra server interaction
        """
        self.ghidra = ghidra_client
        logger.info("Initialized Ghidra tools")
        
    # Information Gathering Tools
    
    def get_function_list(self) -> List[str]:
        """
        Retrieve a list of functions within the analyzed application.
        
        Returns:
            List of function names with their addresses
        """
        return self.ghidra.list_functions()
    
    def get_function_details(self, function_name: str) -> Dict[str, Any]:
        """
        Retrieve detailed information about a specific function.
        
        Args:
            function_name: The name of the function
            
        Returns:
            Dictionary containing function details
        """
        # Get decompiled code
        decompiled_code = self.ghidra.decompile_function(function_name)
        
        # Get address - we may need to extract this from the function name
        # if it follows the pattern FUN_address
        address = None
        if function_name.startswith("FUN_"):
            address = function_name[4:]  # Extract address from FUN_address
        
        # Get disassembly if we have an address
        disassembly = []
        if address:
            disassembly = self.ghidra.disassemble_function(address)
        
        return {
            "name": function_name,
            "address": address,
            "decompiled_code": decompiled_code,
            "disassembly": disassembly
        }
    
    def get_function_details_by_address(self, address: str) -> Dict[str, Any]:
        """
        Retrieve detailed information about a function at a specific address.
        
        Args:
            address: Memory address of the function
            
        Returns:
            Dictionary containing function details
        """
        # Get function name at address
        function_name = self.ghidra.get_function_by_address(address)
        
        # Get decompiled code
        decompiled_code = self.ghidra.decompile_function_by_address(address)
        
        # Get disassembly
        disassembly = self.ghidra.disassemble_function(address)
        
        return {
            "name": function_name,
            "address": address,
            "decompiled_code": decompiled_code,
            "disassembly": disassembly
        }
    
    def get_data_references(self, address: str) -> List[str]:
        """
        Retrieve locations where data at a specific address is referenced.
        
        Args:
            address: Memory address to find references to
            
        Returns:
            List of reference locations
        """
        # This would require implementation in GhidraMCPClient
        # For now, we'll return an empty list
        logger.warning("get_data_references not fully implemented in GhidraMCPClient")
        return []
    
    def get_string_at_address(self, address: str) -> str:
        """
        Retrieve the string located at a specific memory address.
        
        Args:
            address: Memory address containing the string
            
        Returns:
            String value at the address
        """
        # This would require implementation in GhidraMCPClient
        # For now, we'll return a placeholder
        logger.warning("get_string_at_address not fully implemented in GhidraMCPClient")
        return f"String at {address} (not implemented)"
    
    def get_control_flow_graph(self, function_name: str) -> Dict[str, Any]:
        """
        Retrieve the control flow graph of a function.
        
        Args:
            function_name: The name of the function
            
        Returns:
            Control flow graph representation
        """
        # This would require implementation in GhidraMCPClient
        # For now, we'll return a placeholder
        logger.warning("get_control_flow_graph not fully implemented in GhidraMCPClient")
        return {"nodes": [], "edges": []}
    
    def get_memory_regions(self) -> List[str]:
        """
        Retrieve information about the application's memory layout.
        
        Returns:
            List of memory regions
        """
        return self.ghidra.list_segments()
    
    def search_for_pattern(self, pattern: str) -> List[str]:
        """
        Search for a specific byte pattern or string in the application's memory.
        
        Args:
            pattern: Pattern to search for
            
        Returns:
            List of matching locations
        """
        # For string patterns, we can use the search_strings method
        return self.ghidra.safe_get(f"search_strings?pattern={pattern}")
    
    def get_imports(self) -> List[str]:
        """
        Retrieve a list of imported symbols.
        
        Returns:
            List of imported symbols
        """
        return self.ghidra.list_imports()
    
    def get_exports(self) -> List[str]:
        """
        Retrieve a list of exported symbols.
        
        Returns:
            List of exported symbols
        """
        return self.ghidra.list_exports()
    
    # Modification/Annotation Tools
    
    def rename_function(self, function_address: str, new_name: str) -> str:
        """
        Rename a function at the specified address.
        
        Args:
            function_address: Address of the function to rename
            new_name: New name for the function
            
        Returns:
            Result of the rename operation
        """
        return self.ghidra.rename_function_by_address(function_address, new_name)
    
    def add_function_comment(self, address: str, comment: str) -> str:
        """
        Add a comment to a function.
        
        Args:
            address: Address where the comment should be added
            comment: Comment text
            
        Returns:
            Result of the comment operation
        """
        return self.ghidra.set_decompiler_comment(address, comment)
    
    def rename_variable(self, function_address: str, variable_name: str, new_name: str) -> str:
        """
        Rename a local variable in a function.
        
        Args:
            function_address: Address of the function containing the variable
            variable_name: Current name of the variable
            new_name: New name for the variable
            
        Returns:
            Result of the rename operation
        """
        function_name = self.ghidra.get_function_by_address(function_address)
        return self.ghidra.rename_variable(function_name, variable_name, new_name) 