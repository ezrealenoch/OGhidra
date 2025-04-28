#!/usr/bin/env python3
"""
Test script to verify all GhidraMCP endpoints.

This script tests the availability and functionality of all GhidraMCP endpoints
used by the application, providing detailed feedback for each endpoint.
"""

import sys
import os
import time
import argparse
import logging
import json
from collections import namedtuple
import httpx

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define a result type for endpoint tests
EndpointResult = namedtuple('EndpointResult', ['endpoint', 'success', 'status_code', 'message', 'data'])

def test_endpoint(client, server_url, endpoint, method='GET', data=None, params=None, description=None):
    """
    Test a specific GhidraMCP endpoint.
    
    Args:
        client: The httpx client to use
        server_url: Base URL of the GhidraMCP server
        endpoint: The endpoint to test
        method: HTTP method to use (GET or POST)
        data: Data to send for POST requests
        params: Query parameters for GET requests
        description: Human-readable description of what the endpoint does
        
    Returns:
        EndpointResult with the test results
    """
    full_url = f"{server_url}/{endpoint}"
    endpoint_name = description or endpoint
    
    try:
        if method.upper() == 'GET':
            response = client.get(full_url, params=params or {})
        elif method.upper() == 'POST':
            headers = {'Content-Type': 'application/json'} if isinstance(data, dict) else {}
            if isinstance(data, dict):
                response = client.post(full_url, json=data, headers=headers)
            elif isinstance(data, str):
                response = client.post(full_url, data=data.encode('utf-8'), headers={'Content-Type': 'text/plain'})
            else:
                response = client.post(full_url)
        else:
            return EndpointResult(
                endpoint=endpoint, 
                success=False, 
                status_code=None, 
                message=f"Unsupported HTTP method: {method}",
                data=None
            )
            
        # Process response
        if response.status_code == 200:
            try:
                data = response.json()
                return EndpointResult(
                    endpoint=endpoint, 
                    success=True, 
                    status_code=response.status_code, 
                    message=f"{endpoint_name} is available",
                    data=data
                )
            except Exception as e:
                # If not JSON, return text
                return EndpointResult(
                    endpoint=endpoint, 
                    success=True, 
                    status_code=response.status_code, 
                    message=f"{endpoint_name} is available (non-JSON response)",
                    data=response.text
                )
        elif response.status_code == 404:
            return EndpointResult(
                endpoint=endpoint, 
                success=False, 
                status_code=response.status_code, 
                message=f"{endpoint_name} is not implemented in this GhidraMCP server",
                data=None
            )
        else:
            return EndpointResult(
                endpoint=endpoint, 
                success=False, 
                status_code=response.status_code, 
                message=f"{endpoint_name} request failed with status code {response.status_code}",
                data=response.text
            )
            
    except Exception as e:
        return EndpointResult(
            endpoint=endpoint, 
            success=False, 
            status_code=None, 
            message=f"Error testing {endpoint_name}: {str(e)}",
            data=None
        )

def test_all_endpoints(server_url, timeout=10):
    """
    Test all GhidraMCP endpoints used by the application.
    
    Args:
        server_url: Base URL of the GhidraMCP server
        timeout: Connection timeout in seconds
        
    Returns:
        List of EndpointResult objects
    """
    logger.info(f"Testing all GhidraMCP endpoints at {server_url}")
    results = []
    
    try:
        with httpx.Client(timeout=timeout) as client:
            # First check basic connection
            ping_result = test_endpoint(
                client, server_url, "ping", 
                description="Server ping"
            )
            results.append(ping_result)
            
            # If ping failed with connection error, don't try other endpoints
            if not ping_result.success and ping_result.status_code is None:
                logger.error(f"Cannot connect to server at {server_url}")
                return results
                
            # Test core endpoints
            results.append(test_endpoint(
                client, server_url, "list_functions", 
                description="List all functions"
            ))
            
            results.append(test_endpoint(
                client, server_url, "decompile", method="POST", data="main",
                description="Decompile function"
            ))
            
            # Test project management endpoints
            results.append(test_endpoint(
                client, server_url, "list_projects", 
                description="List available projects"
            ))
            
            results.append(test_endpoint(
                client, server_url, "list_programs", 
                description="List programs in current project"
            ))
            
            results.append(test_endpoint(
                client, server_url, "get_current_program", 
                description="Get current program info"
            ))
            
            # Test additional analysis endpoints
            results.append(test_endpoint(
                client, server_url, "list_imports", 
                description="List imported functions"
            ))
            
            results.append(test_endpoint(
                client, server_url, "list_exports", 
                description="List exported functions"
            ))
            
            results.append(test_endpoint(
                client, server_url, "list_classes", 
                description="List classes"
            ))
            
            results.append(test_endpoint(
                client, server_url, "search_strings", params={"pattern": "hello"},
                description="Search for strings"
            ))
            
    except Exception as e:
        logger.error(f"Error during endpoint testing: {e}")
        
    return results

def format_result(result):
    """Format an EndpointResult for display"""
    status = "✅" if result.success else "❌"
    message = result.message
    if result.data and not result.endpoint.startswith("decompile"):  # Skip decompile output as it can be very large
        data_preview = str(result.data)
        if len(data_preview) > 100:
            data_preview = data_preview[:100] + "..."
        message += f"\nResponse: {data_preview}"
    return f"{status} {message}"

def main():
    """Run the GhidraMCP endpoint tests."""
    parser = argparse.ArgumentParser(description="Test GhidraMCP server endpoints")
    parser.add_argument("--url", default="http://127.0.0.1:8080",
                        help="GhidraMCP server URL (default: http://127.0.0.1:8080)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Connection timeout in seconds (default: 10)")
    parser.add_argument("--json", action="store_true",
                        help="Output results in JSON format")
    args = parser.parse_args()
    
    # Run the tests
    results = test_all_endpoints(args.url, timeout=args.timeout)
    
    # Output results
    if args.json:
        json_results = []
        for r in results:
            json_results.append({
                "endpoint": r.endpoint,
                "success": r.success,
                "status_code": r.status_code,
                "message": r.message,
                "data": r.data
            })
        print(json.dumps(json_results, indent=2))
    else:
        print("\nGhidraMCP Endpoint Test Results:")
        print("--------------------------------")
        for result in results:
            print(format_result(result))
            
        # Summary
        success_count = sum(1 for r in results if r.success)
        print("\nSummary:")
        print(f"- {success_count}/{len(results)} endpoints available")
        print(f"- {len(results) - success_count}/{len(results)} endpoints unavailable or failing")
        
        # Recommendations
        if success_count == 0:
            print("\n❌ No endpoints are available. Please ensure the GhidraMCP server is running.")
        elif success_count < len(results):
            print("\n⚠️ Some endpoints are unavailable. This is normal if your GhidraMCP version doesn't support them.")
        else:
            print("\n✅ All tested endpoints are available!")
    
    # Return non-zero exit code if no endpoints are available
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 