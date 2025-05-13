#!/usr/bin/env python3
"""
GhidraMCP API Client
This module provides a client interface for the GhidraMCP API.
It implements the functions defined in the function_signatures.json file.
"""

import requests
import logging
import os
import json
from typing import Dict, List, Optional, Any, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GhidraMCPClient:
    """
    Client for interacting with the GhidraMCP API.
    Implements the functionality defined in function_signatures.json.
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", extended_url: str = "http://localhost:8081"):
        """
        Initialize the GhidraMCP client.
        
        Args:
            base_url: Base URL for the standard GhidraMCP API
            extended_url: Base URL for the extended GhidraMCP API with full function support
        """
        self.base_url = base_url
        self.extended_url = extended_url
        self.function_signatures = self._load_function_signatures()
        
    def _load_function_signatures(self) -> Dict[str, Any]:
        """
        Load function signatures from JSON file.
        
        Returns:
            Dict: Function signatures configuration
        """
        try:
            file_path = os.path.join("ghidra_knowledge_cache", "function_signatures.json")
            with open(file_path, "r") as f:
                return json.load(f)["function_signatures"]
        except Exception as e:
            logger.error(f"Error loading function signatures: {e}")
            return {}
    
    def _get_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, use_extended: bool = True) -> requests.Response:
        """
        Make a GET request to the API.
        
        Args:
            endpoint: API endpoint
            params: Optional query parameters
            use_extended: Whether to try the extended API if the base API fails
            
        Returns:
            Response object from the requests library
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response
        except Exception as e:
            if use_extended:
                try:
                    logger.info(f"Falling back to extended API for {endpoint}")
                    url = f"{self.extended_url}/{endpoint}"
                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    return response
                except Exception as ex:
                    logger.error(f"Error in extended API for {endpoint}: {ex}")
            raise
    
    def _post_request(self, endpoint: str, data: Dict[str, Any], use_extended: bool = True) -> requests.Response:
        """
        Make a POST request to the API.
        
        Args:
            endpoint: API endpoint
            data: Data to send in the request body
            use_extended: Whether to try the extended API if the base API fails
            
        Returns:
            Response object from the requests library
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response
        except Exception as e:
            if use_extended:
                try:
                    logger.info(f"Falling back to extended API for {endpoint}")
                    url = f"{self.extended_url}/{endpoint}"
                    response = requests.post(url, json=data)
                    response.raise_for_status()
                    return response
                except Exception as ex:
                    logger.error(f"Error in extended API for {endpoint}: {ex}")
            raise
    
    def list_functions(self) -> List[str]:
        """
        Lists all functions in the currently loaded program.
        
        Returns:
            List of function names
        """
        try:
            # First try the existing endpoint
            response = self._get_request("methods", use_extended=False)
            functions = response.text.strip().split('\n')
            return functions
        except Exception as e:
            try:
                # Fallback to the functions endpoint on the extended API
                response = self._get_request("functions", use_extended=True)
                return response.json()
            except Exception as ex:
                logger.error(f"Error listing functions: {e}, extended API error: {ex}")
                return []
    
    def decompile_function(self, name: str) -> str:
        """
        Decompiles a function by name using Ghidra's decompiler.
        
        Args:
            name: The name of the function to decompile
            
        Returns:
            C-like representation of the function's code
        """
        try:
            response = self._get_request(f"method/{name}")
            return response.text
        except Exception as e:
            logger.error(f"Error decompiling function {name}: {e}")
            return f"// Error decompiling function: {e}"
    
    def decompile_function_by_address(self, address: str) -> str:
        """
        Decompiles a function at the specified address using Ghidra's decompiler.
        
        Args:
            address: The address of the function to decompile
            
        Returns:
            C-like representation of the function's code
        """
        try:
            response = self._get_request(f"address/{address}")
            return response.text
        except Exception as e:
            logger.error(f"Error decompiling function at address {address}: {e}")
            return f"// Error decompiling function at address {address}: {e}"
    
    def rename_function(self, old_name: str, new_name: str) -> str:
        """
        Renames a function from its current name to a new name.
        
        Args:
            old_name: Current function name
            new_name: New function name
            
        Returns:
            Success message
        """
        try:
            response = self._post_request("rename", {
                "old_name": old_name,
                "new_name": new_name
            })
            
            # Try to parse as JSON, fallback to text
            try:
                return response.json()
            except:
                return response.text
        except Exception as e:
            logger.error(f"Error renaming function {old_name} to {new_name}: {e}")
            return f"Error: {e}"
    
    def rename_function_by_address(self, function_address: str, new_name: str) -> str:
        """
        Renames a function at the specified address to a new name.
        
        Args:
            function_address: The address of the function to rename
            new_name: New function name
            
        Returns:
            Success message
        """
        try:
            response = self._post_request("rename", {
                "function_address": function_address,
                "new_name": new_name
            })
            
            # Try to parse as JSON, fallback to text
            try:
                return response.json()
            except:
                return response.text
        except Exception as e:
            logger.error(f"Error renaming function at address {function_address} to {new_name}: {e}")
            return f"Error: {e}"
    
    def list_imports(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        Lists imported symbols in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of imported symbol names
        """
        try:
            response = self._get_request("imports", {
                "offset": offset,
                "limit": limit
            })
            # Parse the response - assuming it's JSON
            try:
                return response.json()
            except:
                # If the response isn't JSON, try parsing it as text
                return response.text.strip().split('\n')
        except Exception as e:
            logger.error(f"Error listing imports: {e}")
            return []
    
    def list_exports(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        Lists exported functions/symbols in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of exported symbol names
        """
        try:
            response = self._get_request("exports", {
                "offset": offset,
                "limit": limit
            })
            # Parse the response - assuming it's JSON
            try:
                return response.json()
            except:
                # If the response isn't JSON, try parsing it as text
                return response.text.strip().split('\n')
        except Exception as e:
            logger.error(f"Error listing exports: {e}")
            return []
    
    def list_segments(self, offset: int = 0, limit: int = 100) -> List[str]:
        """
        Lists all memory segments in the program with pagination.
        
        Args:
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of memory segment information
        """
        try:
            response = self._get_request("segments", {
                "offset": offset,
                "limit": limit
            })
            # Parse the response - assuming it's JSON
            try:
                return response.json()
            except:
                # If the response isn't JSON, try parsing it as text
                return response.text.strip().split('\n')
        except Exception as e:
            logger.error(f"Error listing segments: {e}")
            return []
    
    def search_functions_by_name(self, query: str, offset: int = 0, limit: int = 100) -> List[str]:
        """
        Searches for functions by name substring.
        
        Args:
            query: Search query string
            offset: Offset to start from
            limit: Maximum number of results
            
        Returns:
            List of matching function names
        """
        try:
            response = self._get_request("functions/search", {
                "query": query,
                "offset": offset,
                "limit": limit
            })
            # Parse the response - assuming it's JSON
            try:
                return response.json()
            except:
                # If the response isn't JSON, try parsing it as text
                return response.text.strip().split('\n')
        except Exception as e:
            logger.error(f"Error searching functions by name: {e}")
            return []
    
    def get_current_function(self) -> str:
        """
        Gets the function at the current cursor position or selection in Ghidra.
        
        Returns:
            Function address and name
        """
        try:
            response = self._get_request("current/function")
            # Parse the response - assuming it's JSON
            try:
                return response.json()
            except:
                # If the response isn't JSON, return it as text
                return response.text
        except Exception as e:
            logger.error(f"Error getting current function: {e}")
            return f"Error: {e}"
    
    def get_current_address(self) -> str:
        """
        Gets the address at the current cursor position in Ghidra.
        
        Returns:
            Current address
        """
        try:
            response = self._get_request("current/address")
            # Parse the response - assuming it's JSON
            try:
                return response.json()
            except:
                # If the response isn't JSON, return it as text
                return response.text
        except Exception as e:
            logger.error(f"Error getting current address: {e}")
            return f"Error: {e}"
    
    def get_bytes(self, address: str, length: int = 16) -> str:
        """
        Gets raw bytes at a specific address.
        
        Args:
            address: The address to read from
            length: Number of bytes to read
            
        Returns:
            Hexadecimal string of bytes
        """
        try:
            response = self._get_request(f"bytes/{address}/{length}")
            return response.text
        except Exception as e:
            logger.error(f"Error getting bytes at address {address}: {e}")
            return f"Error: {e}"
    
    def get_labels(self) -> List[str]:
        """
        Gets all labels in the program.
        
        Returns:
            List of labels
        """
        try:
            response = self._get_request("labels")
            return response.text.strip().split('\n')
        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return []
    
    def get_structures(self) -> str:
        """
        Gets data structures information.
        
        Returns:
            Data structures information
        """
        try:
            response = self._get_request("structures")
            return response.text
        except Exception as e:
            logger.error(f"Error getting structures: {e}")
            return f"Error: {e}"

# Example usage
if __name__ == "__main__":
    client = GhidraMCPClient()
    
    try:
        print("Listing functions:")
        functions = client.list_functions()
        for i, func in enumerate(functions[:5]):  # Show first 5 functions
            print(f"  {i+1}. {func}")
        
        if functions:
            print(f"\nDecompiling first function: {functions[0]}")
            decompiled = client.decompile_function(functions[0])
            print(decompiled[:500] + "..." if len(decompiled) > 500 else decompiled)
            
            # Test renaming function
            first_function = functions[0]
            new_name = f"{first_function}_test"
            print(f"\nRenaming {first_function} to {new_name}")
            result = client.rename_function(first_function, new_name)
            print(f"Result: {result}")
            
            # Rename back
            print(f"\nRenaming {new_name} back to {first_function}")
            result = client.rename_function(new_name, first_function)
            print(f"Result: {result}")
        
        # Test getting bytes
        if functions and '_' in functions[0]:
            address = functions[0].split('_')[1]
            print(f"\nGetting bytes at address {address}:")
            bytes_data = client.get_bytes(address, 16)
            print(bytes_data)
        
        # Test getting structures
        print("\nGetting data structures:")
        structures = client.get_structures()
        print(structures[:500] + "..." if len(structures) > 500 else structures)
        
    except Exception as e:
        print(f"Error: {e}") 