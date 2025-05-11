"""
Client for interacting with the GhidraMCP API.
"""

import json
import logging
import time
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
        self.mock_mode = config.mock_mode
        self.api_version = None
        logger.info(f"Initialized GhidraMCP client at: {config.base_url}")
        
        # Try to detect API version and available endpoints
        if not self.mock_mode:
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
        if self.mock_mode:
            return self._mock_response_list(endpoint, params)
        
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
        if self.mock_mode:
            return self._mock_response_str(endpoint, data)
            
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
    
    def _mock_response_list(self, endpoint: str, params: Dict[str, Any] = None) -> List[str]:
        """Generate a mock list response."""
        logger.info(f"MOCK MODE: GET {endpoint} with params {params}")
        time.sleep(0.5)  # Simulate network delay
        
        if endpoint == "methods":
            return [
                "main",
                "initialize",
                "process_data",
                "cleanup"
            ]
        elif endpoint == "classes":
            return [
                "MainClass",
                "DataProcessor",
                "Logger"
            ]
        elif endpoint == "segments":
            return [
                ".text: 0x1000-0x5000 (rx)",
                ".data: 0x6000-0x7000 (rw)",
                ".rdata: 0x8000-0x9000 (r)"
            ]
        elif endpoint == "imports":
            return [
                "printf (msvcrt.dll)",
                "malloc (msvcrt.dll)",
                "free (msvcrt.dll)"
            ]
        elif endpoint == "exports":
            return [
                "DllMain (0x2000)",
                "ProcessData (0x2100)"
            ]
        elif endpoint == "list_functions":
            return [
                "main (0x1000)",
                "initialize (0x1100)",
                "process_data (0x1200)",
                "cleanup (0x1300)"
            ]
        elif endpoint == "disassemble_function":
            address = params.get("address", "unknown")
            return [
                f"{address}:      push    rbp",
                f"{address}+0x1:  mov     rbp, rsp",
                f"{address}+0x4:  sub     rsp, 0x20",
                f"{address}+0x8:  call    printf",
                f"{address}+0xd:  add     rsp, 0x20",
                f"{address}+0x11: pop     rbp",
                f"{address}+0x12: ret"
            ]
        elif endpoint == "get_function_by_address":
            address = params.get("address", "unknown")
            return [f"function_{address} at {address}"]
        else:
            return [f"Mock response for {endpoint}"]
    
    def _mock_response_str(self, endpoint: str, data: Dict[str, Any] | str) -> str:
        """Generate a mock string response."""
        logger.info(f"MOCK MODE: POST {endpoint} with data {data}")
        time.sleep(0.5)  # Simulate network delay
        
        if endpoint == "decompile":
            name = data if isinstance(data, str) else "unknown"
            return f"// Decompiled function: {name}\nvoid {name}() {{\n    // Mock decompiled code\n    int local_var = 0;\n    printf(\"Hello from function\");\n    return;\n}}"
        elif endpoint == "renameFunction":
            old_name = data.get("oldName", "unknown") if isinstance(data, dict) else "unknown"
            new_name = data.get("newName", "unknown") if isinstance(data, dict) else "unknown"
            return f"Renamed function from {old_name} to {new_name}"
        elif endpoint == "renameData":
            address = data.get("address", "unknown") if isinstance(data, dict) else "unknown"
            new_name = data.get("newName", "unknown") if isinstance(data, dict) else "unknown"
            return f"Renamed data at {address} to {new_name}"
        elif endpoint == "renameVariable":
            function_name = data.get("functionName", "unknown") if isinstance(data, dict) else "unknown"
            old_name = data.get("oldName", "unknown") if isinstance(data, dict) else "unknown"
            new_name = data.get("newName", "unknown") if isinstance(data, dict) else "unknown"
            return f"Renamed variable from {old_name} to {new_name} in function {function_name}"
        else:
            return f"Mock response for {endpoint}"
    
    def health_check(self) -> bool:
        """
        Check if the GhidraMCP server is available.
        
        Returns:
            True if the server is available, False otherwise
        """
        if self.mock_mode:
            return True
            
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