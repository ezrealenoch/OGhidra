#!/usr/bin/env python3
"""
Comprehensive testing script for GhidraMCP connectivity.
Tests all possible endpoints and formats to verify API compatibility.
"""

import os
import sys
import httpx
import time
import json
import logging
from dotenv import load_dotenv
from pprint import pformat

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ghidra-test")

# Configure httpx to log requests
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.INFO)

# Get configuration from environment or use defaults
GHIDRA_MCP_URL = os.getenv("GHIDRA_MCP_URL", "http://localhost:8080")
MAX_RETRIES = 3
TIMEOUT = 10  # seconds

# Test endpoint variations
ENDPOINT_VARIATIONS = {
    # Core functions
    "list_functions": ["functions", "ghidra_list_functions"],
    "get_current_function": ["current_function", "ghidra_get_current_function"],
    "get_current_address": ["current_address", "ghidra_get_current_address"],
    "list_methods": ["methods", "ghidra_list_methods"],
    
    # Class and namespace functions
    "list_classes": ["classes", "ghidra_list_classes"],
    "list_namespaces": ["namespaces", "ghidra_list_namespaces"],
    
    # Import and export functions
    "list_imports": ["imports", "ghidra_list_imports"],
    "list_exports": ["exports", "ghidra_list_exports"],
    
    # Project and program functions
    "list_projects": ["projects", "ghidra_list_projects"],
    "list_programs": ["programs", "ghidra_list_programs"],
    "get_current_program": ["current_program", "ghidra_get_current_program"],
    
    # Decompile functions
    "decompile_function": ["decompile", "ghidra_decompile_function"],
    "decompile_function_by_address": ["decompile_address", "ghidra_decompile_function_by_address"],
    
    # String search
    "search_strings": ["strings", "ghidra_search_strings"],
}

def test_endpoint(base_url, endpoint, method="GET", params=None, data=None, timeout=TIMEOUT):
    """Test if an endpoint exists and log the response."""
    url = f"{base_url}/{endpoint}"
    
    try:
        with httpx.Client() as client:
            logger.info(f"Testing {method} {url}")
            
            if method.upper() == "GET":
                response = client.get(url, params=params, timeout=timeout)
            elif method.upper() == "POST":
                if isinstance(data, dict):
                    response = client.post(url, json=data, timeout=timeout)
                else:
                    response = client.post(url, data=data, timeout=timeout)
            else:
                logger.error(f"Unsupported method: {method}")
                return None
            
            if response.status_code == 200:
                logger.info(f"✅ {endpoint} - SUCCESS")
                
                # Try to parse and pretty print the response
                content_type = response.headers.get("content-type", "")
                content = response.text.strip()
                
                if not content:
                    logger.info("   Empty response")
                    return {"status": "success", "endpoint": endpoint, "response": None}
                    
                # Try parsing as JSON
                if "json" in content_type:
                    try:
                        json_data = response.json()
                        logger.info(f"   JSON response: {pformat(json_data)[:500]}...")
                        return {"status": "success", "endpoint": endpoint, "response": json_data}
                    except json.JSONDecodeError:
                        pass
                
                # Try parsing as lines
                if '\n' in content:
                    lines = content.split('\n')
                    logger.info(f"   {len(lines)} lines in response. First few: {lines[:3]}")
                    
                    # Look for mock data patterns
                    mock_patterns = ["malware.exe", "hello world", "test_func"]
                    if any(any(pattern in line.lower() for pattern in mock_patterns) for line in lines):
                        logger.warning("   ⚠️ Response appears to contain test/mock data")
                    
                    return {"status": "success", "endpoint": endpoint, "response": lines}
                else:
                    # Simple string response
                    logger.info(f"   String response: {content[:500]}...")
                    return {"status": "success", "endpoint": endpoint, "response": content}
            else:
                # Log failures but don't fail completely
                logger.warning(f"❌ {endpoint} - FAILED with status {response.status_code}: {response.text[:200]}...")
                return {"status": "error", "endpoint": endpoint, "error": f"Status {response.status_code}", "response": response.text}
    except Exception as e:
        logger.error(f"❌ {endpoint} - ERROR: {str(e)}")
        return {"status": "error", "endpoint": endpoint, "error": str(e)}

def test_all_endpoint_variations():
    """Test all endpoint variations to find which ones work."""
    results = {}
    supported_endpoints = []
    
    for base_endpoint, variations in ENDPOINT_VARIATIONS.items():
        # Add the base endpoint to the variations to test
        all_variations = [base_endpoint] + variations
        
        for endpoint in all_variations:
            result = test_endpoint(GHIDRA_MCP_URL, endpoint)
            
            if result and result.get("status") == "success":
                supported_endpoints.append(endpoint)
                
                # For successful endpoints, also try with parameters if needed
                if endpoint in ["decompile_function", "decompile_function_by_address"]:
                    # First try to get a function name or address from list_functions
                    functions_result = test_endpoint(GHIDRA_MCP_URL, "list_functions")
                    if functions_result and functions_result.get("status") == "success":
                        functions = functions_result.get("response", [])
                        if functions and isinstance(functions, list) and len(functions) > 0:
                            # Try to extract a function name or address
                            function_info = functions[0]
                            if ' at ' in function_info:
                                # Format is usually "FUN_00401000 at 00401000"
                                parts = function_info.split(' at ')
                                if len(parts) == 2:
                                    name = parts[0].strip()
                                    address = parts[1].strip()
                                    
                                    # Test decompile by name
                                    if endpoint == "decompile_function":
                                        test_endpoint(GHIDRA_MCP_URL, endpoint, method="POST", data=name)
                                    
                                    # Test decompile by address
                                    if endpoint == "decompile_function_by_address":
                                        test_endpoint(GHIDRA_MCP_URL, endpoint, params={"address": address})
            
            # Store all results
            if result:
                results[endpoint] = result
    
    return {
        "results": results,
        "supported_endpoints": supported_endpoints
    }

def check_connection_compatibility():
    """Determine which endpoint naming format is used by the server."""
    logger.info(f"Testing GhidraMCP server connectivity at {GHIDRA_MCP_URL}...")
    
    # Test all endpoint variations
    all_results = test_all_endpoint_variations()
    supported = all_results.get("supported_endpoints", [])
    
    if not supported:
        logger.error(f"Failed to connect to any GhidraMCP endpoint at {GHIDRA_MCP_URL}")
        logger.info("""
Troubleshooting tips:
1. Make sure Ghidra is running
2. Check that the GhidraMCP plugin is installed and enabled in Ghidra
3. In Ghidra, go to Edit -> Tool Options -> GhidraMCP HTTP Server to verify server settings
4. Ensure the server has been started (Window -> GhidraMCP Server -> Start Server)
5. Check that the port in your .env file (GHIDRA_MCP_URL) matches Ghidra's configuration
6. Verify the Ghidra server logs for any errors
""")
        return False
    
    # Analyze supported endpoints to determine pattern
    logger.info(f"Successfully connected to GhidraMCP server!")
    logger.info(f"Supported endpoints ({len(supported)}): {supported}")
    
    # Check prefix patterns
    has_ghidra_prefix = any(endpoint.startswith("ghidra_") for endpoint in supported)
    has_no_prefix = any(not endpoint.startswith("ghidra_") and "_" not in endpoint for endpoint in supported)
    
    if has_ghidra_prefix:
        logger.info("This server appears to use the 'ghidra_' prefix for endpoints")
    elif has_no_prefix:
        logger.info("This server appears to use short names without prefixes")
    else:
        logger.info("Could not determine endpoint naming pattern")
    
    # Check if we get mock data
    mock_responses = []
    results = all_results.get("results", {})
    for endpoint, result in results.items():
        if result.get("status") == "success":
            response = result.get("response")
            if isinstance(response, list):
                # Check for mock data patterns
                mock_patterns = ["malware.exe", "hello world", "test_func"]
                if any(any(pattern in str(line).lower() for pattern in mock_patterns) for line in response):
                    mock_responses.append(endpoint)
    
    if mock_responses:
        logger.warning(f"⚠️ Mock/test data detected in these endpoints: {mock_responses}")
        logger.warning("GhidraMCP may not be analyzing a real binary or may be in test mode")
    
    return True

def main():
    """Run the test."""
    try:
        if check_connection_compatibility():
            logger.info("GhidraMCP connectivity test completed successfully")
            return 0
        else:
            logger.error("GhidraMCP connectivity test failed")
            return 1
    except Exception as e:
        logger.exception(f"Unexpected error during test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 