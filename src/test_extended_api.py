#!/usr/bin/env python3
"""
Test script for the Extended GhidraMCP API.
Tests the full implementation that supports all function signatures.
"""

import json
import requests
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ExtendedGhidraMCPTester:
    def __init__(self, base_url: str = "http://localhost:8081"):
        """Initialize the tester with the extended API server."""
        self.base_url = base_url
        
    def test_api_documentation(self) -> Dict[str, Any]:
        """Test the root endpoint for API documentation."""
        try:
            response = requests.get(f"{self.base_url}/")
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "object",
                "description": "API documentation with list of endpoints"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_get_methods(self) -> Dict[str, Any]:
        """Test /methods endpoint to get all function names."""
        try:
            response = requests.get(f"{self.base_url}/methods")
            response.raise_for_status()
            
            # Response is a text list of method names, one per line
            methods = response.text.strip().split('\n')
            
            return {
                "success": True,
                "data": methods,
                "type": "string[]",
                "description": "Returns list of all function names in the program"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_decompile_function(self) -> Dict[str, Any]:
        """Test decompile_function endpoint."""
        try:
            # First get a list of methods to test with
            methods = self.test_get_methods()
            if not methods.get("success"):
                return {"success": False, "error": "Could not get method list"}
            
            # Use the first method for testing
            test_function = methods["data"][0] if methods["data"] else "FUN_140001000"
            
            response = requests.get(
                f"{self.base_url}/method/{test_function}"
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.text,
                "type": "string",
                "description": "Returns decompiled C-like code as a string"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_decompile_function_by_address(self) -> Dict[str, Any]:
        """Test decompile_function_by_address endpoint."""
        try:
            # First get a function address to test with
            methods = self.test_get_methods()
            if not methods.get("success"):
                return {"success": False, "error": "Could not get method list"}
            
            # Extract address from function name (assuming format like FUN_140001030)
            test_function = methods["data"][0] if methods["data"] else "FUN_140001000"
            test_address = test_function.split('_')[1] if '_' in test_function else "140001000"
            
            response = requests.get(
                f"{self.base_url}/address/{test_address}"
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.text,
                "type": "string",
                "description": "Returns decompiled C-like code as a string"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_rename_function(self) -> Dict[str, Any]:
        """Test rename_function endpoint."""
        try:
            # First get a list of methods to test with
            methods = self.test_get_methods()
            if not methods.get("success"):
                return {"success": False, "error": "Could not get method list"}
            
            # Use the first method for testing
            test_function = methods["data"][0] if methods["data"] else "FUN_140001000"
            new_name = f"{test_function}_renamed"
            
            response = requests.post(
                f"{self.base_url}/rename",
                json={
                    "old_name": test_function,
                    "new_name": new_name
                }
            )
            response.raise_for_status()
            
            # Rename it back to keep our test data clean
            requests.post(
                f"{self.base_url}/rename",
                json={
                    "old_name": new_name,
                    "new_name": test_function
                }
            )
            
            return {
                "success": True,
                "data": response.json(),
                "type": "object",
                "description": "Returns success message"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_rename_function_by_address(self) -> Dict[str, Any]:
        """Test rename_function_by_address endpoint."""
        try:
            # First get a function address to test with
            methods = self.test_get_methods()
            if not methods.get("success"):
                return {"success": False, "error": "Could not get method list"}
            
            # Extract address from function name (assuming format like FUN_140001030)
            test_function = methods["data"][0] if methods["data"] else "FUN_140001000"
            test_address = test_function.split('_')[1] if '_' in test_function else "140001000"
            new_name = f"func_{test_address}_renamed"
            
            response = requests.post(
                f"{self.base_url}/rename",
                json={
                    "function_address": test_address,
                    "new_name": new_name
                }
            )
            response.raise_for_status()
            
            # Rename it back to keep our test data clean
            requests.post(
                f"{self.base_url}/rename",
                json={
                    "old_name": new_name,
                    "new_name": test_function
                }
            )
            
            return {
                "success": True,
                "data": response.json(),
                "type": "object",
                "description": "Returns success message"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_list_functions(self) -> Dict[str, Any]:
        """Test list_functions endpoint."""
        try:
            response = requests.get(f"{self.base_url}/functions")
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string[]",
                "description": "Returns array of function names"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_search_functions_by_name(self) -> Dict[str, Any]:
        """Test search_functions_by_name endpoint."""
        try:
            response = requests.get(
                f"{self.base_url}/functions/search",
                params={
                    "query": "FUN",
                    "offset": 0,
                    "limit": 10
                }
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string[]",
                "description": "Returns array of matching function names"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_list_imports(self) -> Dict[str, Any]:
        """Test list_imports endpoint."""
        try:
            response = requests.get(
                f"{self.base_url}/imports",
                params={"offset": 0, "limit": 10}
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string[]",
                "description": "Returns array of imported symbol names"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_list_exports(self) -> Dict[str, Any]:
        """Test list_exports endpoint."""
        try:
            response = requests.get(
                f"{self.base_url}/exports",
                params={"offset": 0, "limit": 10}
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string[]",
                "description": "Returns array of exported symbol names"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_list_segments(self) -> Dict[str, Any]:
        """Test list_segments endpoint."""
        try:
            response = requests.get(
                f"{self.base_url}/segments",
                params={"offset": 0, "limit": 10}
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string[]",
                "description": "Returns array of segment information"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_get_current_function(self) -> Dict[str, Any]:
        """Test get_current_function endpoint."""
        try:
            response = requests.get(f"{self.base_url}/current/function")
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string",
                "description": "Returns current function name and address"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_get_current_address(self) -> Dict[str, Any]:
        """Test get_current_address endpoint."""
        try:
            response = requests.get(f"{self.base_url}/current/address")
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "type": "string",
                "description": "Returns current address"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_get_bytes(self) -> Dict[str, Any]:
        """Test get_bytes endpoint."""
        try:
            # First get a function address to test with
            methods = self.test_get_methods()
            if not methods.get("success"):
                return {"success": False, "error": "Could not get method list"}
            
            # Extract address from function name (assuming format like FUN_140001030)
            test_function = methods["data"][0] if methods["data"] else "FUN_140001000"
            test_address = test_function.split('_')[1] if '_' in test_function else "140001000"
            
            response = requests.get(
                f"{self.base_url}/bytes/{test_address}/16"
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.text,
                "type": "string",
                "description": "Returns raw bytes at a specific address"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_get_labels(self) -> Dict[str, Any]:
        """Test get_labels endpoint."""
        try:
            response = requests.get(f"{self.base_url}/labels")
            response.raise_for_status()
            return {
                "success": True,
                "data": response.text,
                "type": "string",
                "description": "Returns all labels in the program"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_get_structures(self) -> Dict[str, Any]:
        """Test get_structures endpoint."""
        try:
            response = requests.get(f"{self.base_url}/structures")
            response.raise_for_status()
            return {
                "success": True,
                "data": response.text,
                "type": "string",
                "description": "Returns data structures information"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_all_tests(self):
        """Run all function tests and print results."""
        test_functions = {
            "api_documentation": self.test_api_documentation,
            "get_methods": self.test_get_methods,
            "decompile_function": self.test_decompile_function,
            "decompile_function_by_address": self.test_decompile_function_by_address,
            "rename_function": self.test_rename_function,
            "rename_function_by_address": self.test_rename_function_by_address,
            "list_functions": self.test_list_functions,
            "search_functions_by_name": self.test_search_functions_by_name,
            "list_imports": self.test_list_imports,
            "list_exports": self.test_list_exports,
            "list_segments": self.test_list_segments,
            "get_current_function": self.test_get_current_function,
            "get_current_address": self.test_get_current_address,
            "get_bytes": self.test_get_bytes,
            "get_labels": self.test_get_labels,
            "get_structures": self.test_get_structures
        }

        print("\n=== Extended GhidraMCP API Tests ===\n")
        
        successful_tests = 0
        failed_tests = 0
        
        for func_name, test_func in test_functions.items():
            print(f"\nTesting {func_name}...")
            result = test_func()
            
            if result["success"]:
                successful_tests += 1
                print(f"✅ Success")
                print(f"Return type: {result['type']}")
                print(f"Description: {result['description']}")
                if isinstance(result['data'], list):
                    sample_data = result['data'][:3] if result['data'] else '[]'
                    print(f"Sample data: {sample_data}")
                elif isinstance(result['data'], dict):
                    try:
                        keys = list(result['data'].keys())[:3]
                        sample_data = {k: result['data'][k] for k in keys}
                        print(f"Sample data: {sample_data}")
                    except:
                        print(f"Sample data: {str(result['data'])[:100]}")
                else:
                    data_sample = str(result['data'])[:100]
                    print(f"Sample data: {data_sample}..." if len(data_sample) >= 100 else f"Sample data: {data_sample}")
            else:
                failed_tests += 1
                print(f"❌ Failed: {result['error']}")
            
            print("-" * 50)
        
        print(f"\nTest Summary:")
        print(f"✅ Successful tests: {successful_tests}")
        print(f"❌ Failed tests: {failed_tests}")
        print(f"Total tests: {successful_tests + failed_tests}")
        print(f"Success rate: {successful_tests / (successful_tests + failed_tests) * 100:.2f}%")

def main():
    """Main entry point."""
    tester = ExtendedGhidraMCPTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 