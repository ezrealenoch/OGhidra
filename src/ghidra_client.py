"""
Client for interacting with the GhidraMCP API.
"""

import json
import logging
import time
import re
from typing import Dict, Any, List, Optional

import httpx

from src.config import GhidraMCPConfig

logger = logging.getLogger("ollama-ghidra-bridge.ghidra")

class GhidraMCPClient:
    """Client for interacting with GhidraMCP API."""
    
    def __init__(self, config: GhidraMCPConfig):
        """
        Initialize the GhidraMCP client.
        
        Args:
            config: GhidraMCPConfig object with connection details
        """
        self.config = config
        self.client = httpx.Client(timeout=config.timeout)
        self.api_version = None
        logger.info(f"Initialized GhidraMCP client at: {config.base_url}")
        
        # Try to detect API version and available endpoints
        self._detect_api()
    
    def _detect_api(self):
        """Detect the API version and available endpoints."""
        try:
            # Try to get available methods
            response = self.safe_get("methods", {"offset": 0, "limit": 1})
            if response and not response[0].startswith("Error"):
                logger.info("Successfully connected to GhidraMCP API")
            else:
                logger.warning(f"Failed to connect to GhidraMCP API: {response}")
        except Exception as e:
            logger.warning(f"Error detecting API: {str(e)}")
    
    def safe_get(self, endpoint: str, params: Dict[str, Any] = None) -> List[str]:
        """
        Perform a GET request with optional query parameters.
        
        Args:
            endpoint: The endpoint to request
            params: Optional query parameters
            
        Returns:
            List of response lines
        """
        if params is None:
            params = {}
            
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            logger.debug(f"Sending GET request to GhidraMCP: {endpoint} with params: {params}")
            response = self.client.get(url, params=params, timeout=self.config.timeout)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                return response.text.splitlines()
            else:
                return [f"Error {response.status_code}: {response.text.strip()}"]
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return [error_msg]
    
    def safe_post(self, endpoint: str, data: Dict[str, Any] | str) -> str:
        """
        Perform a POST request with data.
        
        Args:
            endpoint: The endpoint to request
            data: Data to send (dict or string)
            
        Returns:
            Response text
        """
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            logger.debug(f"Sending POST request to GhidraMCP: {endpoint} with data: {data}")
            
            if isinstance(data, dict):
                response = self.client.post(url, data=data, timeout=self.config.timeout)
            else:
                response = self.client.post(url, data=data.encode("utf-8"), timeout=self.config.timeout)
            
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                return response.text.strip()
            else:
                return f"Error {response.status_code}: {response.text.strip()}"
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def health_check(self) -> bool:
        """
        Check if the GhidraMCP server is available.
        
        Returns:
            True if the server is available, False otherwise
        """
        try:
            response = self.safe_get("methods", {"offset": 0, "limit": 1})
            return response and not response[0].startswith("Error")
        except Exception as e:
            logger.error(f"GhidraMCP server health check failed: {str(e)}")
            return False
    
    def check_health(self) -> bool:
        """
        Check if the GhidraMCP server is reachable and responding.
        
        Returns:
            True if GhidraMCP is healthy, False otherwise
        """
        try:
            # Try a simple endpoint like listing first method as a health check
            response = self.client.get(f"{self.config.base_url}/methods", params={"offset": 0, "limit": 1})
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"GhidraMCP health check failed: {str(e)}")
            return False
    
    # Implement GhidraMCP API methods
    
    def list_methods(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List all function names in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of function names
        """
        return self.safe_get("methods", {"offset": offset, "limit": limit})
    
    def list_classes(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List all namespace/class names in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of class names
        """
        return self.safe_get("classes", {"offset": offset, "limit": limit})
    
    def decompile_function(self, name: str) -> str:
        """
        Decompile a specific function by name and return the decompiled C code.
        
        Args:
            name: Function name
            
        Returns:
            Decompiled C code
        """
        return self.safe_post("decompile", name)
    
    def rename_function(self, old_name: str, new_name: str) -> str:
        """
        Rename a function by its current name to a new user-defined name.
        
        Args:
            old_name: Current function name
            new_name: New function name
            
        Returns:
            Result of the rename operation
        """
        return self.safe_post("renameFunction", {"oldName": old_name, "newName": new_name})
    
    def rename_data(self, address: str, new_name: str) -> str:
        """
        Rename a data label at the specified address.
        
        Args:
            address: Data address
            new_name: New data name
            
        Returns:
            Result of the rename operation
        """
        return self.safe_post("renameData", {"address": address, "newName": new_name})
    
    def list_segments(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List all memory segments in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of memory segments
        """
        return self.safe_get("segments", {"offset": offset, "limit": limit})
    
    def list_imports(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List imported symbols in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of imported symbols
        """
        return self.safe_get("imports", {"offset": offset, "limit": limit})
    
    def list_exports(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List exported functions/symbols with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of exported symbols
        """
        return self.safe_get("exports", {"offset": offset, "limit": limit})
    
    def list_namespaces(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List all non-global namespaces in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of namespaces
        """
        return self.safe_get("namespaces", {"offset": offset, "limit": limit})
    
    def list_data_items(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List defined data labels and their values with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of data items
        """
        return self.safe_get("data", {"offset": offset, "limit": limit})
    
    def list_strings(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        List all strings in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of strings
        """
        return self.safe_get("strings", {"offset": offset, "limit": limit})
    
    def search_functions_by_name(self, query: str, offset: int = 0, limit: int = 100) -> List[str]:
        """
        Search for functions whose name contains the given substring.
        
        Args:
            query: Search query
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of matching functions
        """
        if not query:
            return ["Error: query string is required"]
        return self.safe_get("searchFunctions", {"query": query, "offset": offset, "limit": limit})
    
    def rename_variable(self, function_name: str, old_name: str, new_name: str) -> str:
        """
        Rename a local variable within a function.
        
        Args:
            function_name: Function name
            old_name: Current variable name
            new_name: New variable name
            
        Returns:
            Result of the rename operation
        """
        return self.safe_post("renameVariable", {
            "functionName": function_name,
            "oldName": old_name,
            "newName": new_name
        })
    
    def get_function_by_address(self, address: str) -> str:
        """
        Get a function by its address.
        
        Args:
            address: Function address
            
        Returns:
            Function information
        """
        result = self.safe_get("get_function_by_address", {"address": address})
        return "\n".join(result)
    
    def get_current_address(self) -> str:
        """
        Get the address currently selected by the user.
        
        Returns:
            Current address
        """
        result = self.safe_get("get_current_address")
        return "\n".join(result)
    
    def get_current_function(self) -> str:
        """
        Get the function currently selected by the user.
        
        Returns:
            Current function
        """
        result = self.safe_get("get_current_function")
        return "\n".join(result)
    
    def list_functions(self) -> List[str]:
        """
        List all functions in the database.
        
        Returns:
            List of functions
        """
        return self.safe_get("list_functions")
    
    def decompile_function_by_address(self, address: str) -> str:
        """
        Decompile a function at the given address.
        
        Args:
            address: Function address
            
        Returns:
            Decompiled function
        """
        result = self.safe_get("decompile_function", {"address": address})
        return "\n".join(result)
    
    def analyze_function(self, address: str = None) -> str:
        """
        Analyze a function, including its decompiled code and all functions it calls.
        If no address is provided, uses the current function.
        
        Args:
            address: Function address (optional)
            
        Returns:
            Comprehensive function analysis including decompiled code and referenced functions
        """
        if address is None:
            determined_address = None
            # Try with get_current_function() first
            current_function_info = self.get_current_function() # Expected: "FunctionName @ Address" or error string
            
            if not current_function_info.startswith("Error"):
                if "@ " in current_function_info:
                    parts = current_function_info.split("@ ", 1)
                    if len(parts) == 2:
                        potential_address = parts[1].strip()
                        # Validate if the extracted address is a non-empty hex string
                        if potential_address and all(c in "0123456789abcdefABCDEF" for c in potential_address):
                            determined_address = potential_address
                            logger.info(f"analyze_function: Determined address '{determined_address}' from get_current_function() result: '{current_function_info}'.")
                        else:
                            logger.warning(f"analyze_function: Extracted part '{potential_address}' from get_current_function() result ('{current_function_info}') is not a valid hex address.")
                    else:
                        # This case should ideally not be reached if "@ " is present and split is limited to 1
                        logger.warning(f"analyze_function: Unexpected split result from get_current_function() ('{current_function_info}') despite '@ ' being present.")
                else:
                    logger.warning(f"analyze_function: Result from get_current_function() ('{current_function_info}') does not contain '@ '. Attempting get_current_address().")
            else:
                logger.warning(f"analyze_function: get_current_function() returned an error: '{current_function_info}'. Attempting get_current_address().")

            # If get_current_function() didn't yield a valid address, try get_current_address()
            if determined_address is None:
                logger.info("analyze_function: Trying get_current_address() as fallback to determine function address.")
                current_address_str = self.get_current_address() # Expected: "Address" or error string
                # Validate if current_address_str is a non-empty hex string and not an error
                if not current_address_str.startswith("Error") and current_address_str and all(c in "0123456789abcdefABCDEF" for c in current_address_str):
                    determined_address = current_address_str
                    logger.info(f"analyze_function: Determined address '{determined_address}' from get_current_address().")
                else:
                    logger.warning(f"analyze_function: get_current_address() did not yield a valid hex address. Result: '{current_address_str}'")
            
            if determined_address:
                address = determined_address
            else:
                logger.error("analyze_function: Could not determine current function address automatically after trying get_current_function() and get_current_address().")
                return "Error: Could not determine current function address. Please provide an address or ensure a function/address is selected in Ghidra."
        
        # Get the decompiled code for the target function
        decompiled_code = self.decompile_function_by_address(address)
        if decompiled_code.startswith("Error"):
            return f"Error analyzing function at {address}: {decompiled_code}"
            
        # Extract function calls from the decompiled code
        function_calls = []
        for line in decompiled_code.splitlines():
            matches = re.finditer(r'\b(\w+)\s*\(', line)
            for match in matches:
                func_name = match.group(1)
                if func_name not in ["if", "while", "for", "switch", "return", "sizeof"]:
                    function_calls.append(func_name)
        
        function_calls = list(set(function_calls))
        
        result = [f"=== ANALYSIS OF FUNCTION AT {address} ===", "", decompiled_code, "", "=== REFERENCED FUNCTIONS ===", ""]
        
        for func_name in function_calls:
            try:
                func_code = self.decompile_function(func_name)
                if not func_code.startswith("Error"):
                    result.append(f"--- Function: {func_name} ---")
                    result.append(func_code)
                    result.append("")
            except Exception as e:
                logger.debug(f"Could not decompile referenced function {func_name}: {e}")
        
        return "\n".join(result)
    
    def disassemble_function(self, address: str) -> List[str]:
        """
        Get assembly code (address: instruction; comment) for a function.
        
        Args:
            address: Function address
            
        Returns:
            Disassembled function
        """
        return self.safe_get("disassemble_function", {"address": address})
    
    def set_decompiler_comment(self, address: str, comment: str) -> str:
        """
        Set a comment for a given address in the function pseudocode.
        
        Args:
            address: Address
            comment: Comment
            
        Returns:
            Result of the operation
        """
        return self.safe_post("set_decompiler_comment", {"address": address, "comment": comment})
    
    def set_disassembly_comment(self, address: str, comment: str) -> str:
        """
        Set a comment for a given address in the function disassembly.
        
        Args:
            address: Address
            comment: Comment
            
        Returns:
            Result of the operation
        """
        return self.safe_post("set_disassembly_comment", {"address": address, "comment": comment})
    
    def rename_function_by_address(self, function_address: str, new_name: str) -> str:
        """
        Rename a function by its address.
        
        Args:
            function_address: Function address
            new_name: New name
            
        Returns:
            Result of the rename operation
        """
        return self.safe_post("rename_function_by_address", {"function_address": function_address, "new_name": new_name})
    
    def set_function_prototype(self, function_address: str, prototype: str) -> str:
        """
        Set a function's prototype.
        
        Args:
            function_address: Function address
            prototype: Function prototype
            
        Returns:
            Result of the operation
        """
        return self.safe_post("set_function_prototype", {"function_address": function_address, "prototype": prototype})
    
    def set_local_variable_type(self, function_address: str, variable_name: str, new_type: str) -> str:
        """
        Set a local variable's type.
        
        Args:
            function_address: Function address
            variable_name: Variable name
            new_type: New type
            
        Returns:
            Result of the operation
        """
        return self.safe_post("set_local_variable_type", {
            "function_address": function_address,
            "variable_name": variable_name,
            "new_type": new_type
        }) 