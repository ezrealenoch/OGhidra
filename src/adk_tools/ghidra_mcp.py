"""
ADK Tools for interacting with the GhidraMCP server.

These tools provide a structured interface for the ADK agent
to call functions within a running Ghidra instance via the GhidraMCP bridge.
"""

import os
import httpx
import logging
import time
from typing import List, Dict, Any, Optional

# Configure basic logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# --- GhidraMCP Configuration ---
GHIDRA_MCP_BASE_URL = os.getenv("GHIDRA_MCP_URL", "http://localhost:8080")
GHIDRA_MCP_TIMEOUT = int(os.getenv("GHIDRA_MCP_TIMEOUT", "60")) # Increased timeout for potentially long operations
MAX_CONNECTION_RETRIES = int(os.getenv("GHIDRA_MCP_RETRIES", "3"))

# Attempt to connect to GhidraMCP server on module load
def verify_ghidra_mcp_connection(max_retries=MAX_CONNECTION_RETRIES, retry_delay=2) -> Dict[str, Any]:
    """
    Verifies that the GhidraMCP server is running and accessible.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay in seconds between retries
        
    Returns:
        A dictionary: {'status': 'success', 'result': 'Connected to GhidraMCP server at <url>'}
        or {'status': 'error', 'message': '<error details>'}
    """
    logger.info(f"Verifying connection to GhidraMCP server at {GHIDRA_MCP_BASE_URL}")
    
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=10) as client:  # Short timeout for quick check
                response = client.get(f"{GHIDRA_MCP_BASE_URL}/ping")
                
                if response.status_code == 200:
                    logger.info(f"Successfully connected to GhidraMCP server at {GHIDRA_MCP_BASE_URL}")
                    return {"status": "success", "result": f"Connected to GhidraMCP server at {GHIDRA_MCP_BASE_URL}"}
                else:
                    logger.warning(f"GhidraMCP server responded with status code {response.status_code}")
        except httpx.RequestError as exc:
            logger.warning(f"Unable to connect to GhidraMCP server (attempt {attempt+1}/{max_retries}): {exc}")
            
        if attempt < max_retries - 1:
            logger.info(f"Retrying connection in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    error_message = f"Failed to connect to GhidraMCP server at {GHIDRA_MCP_BASE_URL} after {max_retries} attempts. " \
                   f"Please ensure that:\n" \
                   f"1. Ghidra is running\n" \
                   f"2. The GhidraMCP plugin is installed and enabled\n" \
                   f"3. The server is configured to run on {GHIDRA_MCP_BASE_URL}\n" \
                   f"You can verify the port in Ghidra using Edit -> Tool Options -> GhidraMCP HTTP Server"
    logger.error(error_message)
    return {"status": "error", "message": error_message}

# Try to verify connection at module load time
connection_status = verify_ghidra_mcp_connection()
if connection_status["status"] == "error":
    logger.warning("Operating in disconnected mode. Some functions may not work properly.")

# --- Internal Helper Functions ---

def _make_ghidra_request(
    endpoint: str,
    params: Dict = None,
    data: Dict = None,
    method: str = "GET",
    retries: int = MAX_CONNECTION_RETRIES,
    retry_delay: float = 1.0,
    allow_endpoint_fallback: bool = True
) -> Dict[str, Any]:
    """
    Make a request to the GhidraMCP server with retries and endpoint fallback.
    
    Args:
        endpoint: The endpoint to request (with or without 'ghidra_' prefix)
        params: URL parameters for the request
        data: JSON data for the request
        method: HTTP method to use (GET or POST)
        retries: Number of retries on connection errors
        retry_delay: Delay between retries in seconds
        allow_endpoint_fallback: Whether to try alternate endpoint format if first fails
        
    Returns:
        Dict: Response from GhidraMCP containing status and result
    """
    # Handle mock mode
    if MOCK_MODE:
        return _get_mock_response(endpoint, params, data)
        
    # Set up request details
    url = f"{GHIDRA_MCP_BASE_URL}/{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    # First attempt with original endpoint
    response_data = _try_request(url, params, data, method, headers, retries, retry_delay)
    
    # If endpoint not found and fallback allowed, try with/without ghidra_ prefix
    if (response_data.get("status") == "error" and 
        response_data.get("error_type") == "endpoint_not_found" and 
        allow_endpoint_fallback):
        
        # Determine alternate endpoint name
        if endpoint.startswith("ghidra_"):
            alternate_endpoint = endpoint[len("ghidra_"):]
            logger.debug(f"Trying alternate endpoint without prefix: {alternate_endpoint}")
        else:
            alternate_endpoint = f"ghidra_{endpoint}"
            logger.debug(f"Trying alternate endpoint with prefix: {alternate_endpoint}")
        
        # Try the alternate endpoint
        alt_url = f"{GHIDRA_MCP_BASE_URL}/{alternate_endpoint}"
        alt_response = _try_request(alt_url, params, data, method, headers, retries, retry_delay)
        
        # If alternate endpoint succeeded, return its result
        if alt_response.get("status") == "success":
            logger.info(f"Request succeeded with alternate endpoint: {alternate_endpoint}")
            return alt_response
        else:
            # Both endpoints failed, return original error
            logger.error(f"Both endpoints failed: {endpoint} and {alternate_endpoint}")
            return response_data
    
    # Return result from original endpoint attempt
    return response_data

def _try_request(
    url: str, 
    params: Dict, 
    data: Dict, 
    method: str,
    headers: Dict,
    retries: int,
    retry_delay: float
) -> Dict[str, Any]:
    """
    Helper function to attempt a request with retries.
    
    Args:
        url: Full URL to request
        params: URL parameters
        data: JSON data for request body
        method: HTTP method
        headers: Request headers
        retries: Number of retries for connection errors
        retry_delay: Delay between retries in seconds
        
    Returns:
        Dict: Response data with status and result
    """
    attempt = 0
    
    while attempt <= retries:
        try:
            logger.debug(f"Requesting {url} (attempt {attempt+1}/{retries+1})")
            
            if method.upper() == "GET":
                response = httpx.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                response = httpx.post(url, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
            
            # Check response status code
            if response.status_code == 200:
                # Successful response with content
                try:
                    result = response.json()
                    return {"status": "success", "result": result}
                except ValueError:
                    return {"status": "error", "error_type": "invalid_json", "message": f"Invalid JSON response: {response.text[:100]}"}
            
            elif response.status_code == 204:
                # Successful response with no content
                return {"status": "success", "result": None}
            
            elif response.status_code == 404:
                # Endpoint not found - but check if we got valid JSON data anyway
                # Some GhidraMCP implementations return 404 with valid content
                try:
                    result = response.json()
                    if isinstance(result, dict) and "error" not in result:
                        logger.warning(f"Endpoint {url} returned 404 but contained valid data. Using the data anyway.")
                        return {"status": "success", "result": result}
                    else:
                        logger.warning(f"Endpoint not found: {url}")
                        return {"status": "error", "error_type": "endpoint_not_found", "message": f"Endpoint not found: {url}"}
                except ValueError:
                    logger.warning(f"Endpoint not found: {url}")
                    return {"status": "error", "error_type": "endpoint_not_found", "message": f"Endpoint not found: {url}"}
            
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check for 404 specifically to handle missing endpoints gracefully
            if response.status_code == 404:
                logger.warning(f"Endpoint {endpoint} not found in GhidraMCP server. This may be because the server doesn't implement this functionality yet.")
                return {
                    "status": "error", 
                    "message": f"Endpoint '{endpoint}' not available in the GhidraMCP server. The server may need to be updated."
                }
                
            response.raise_for_status() # Raise HTTPStatusError for other 4xx/5xx responses

            # Process successful response
            try:
                # Try parsing as JSON first, handle potential errors
                result_data = response.json()
            except ValueError:
                 # If not JSON, treat as text and split lines
                result_data = response.text.splitlines()
                # If it's a single line of simple text, just return that string
                if isinstance(result_data, list) and len(result_data) == 1:
                     if not any(c in result_data[0] for c in ['\n', '{', '[']): # Heuristic for simple string
                           result_data = result_data[0]


            return {"status": "success", "result": result_data}

    except httpx.HTTPStatusError as exc:
        error_message = f"GhidraMCP Error {exc.response.status_code}: {exc.response.text[:500]}" # Limit error text length
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    except httpx.RequestError as exc:
        error_message = f"GhidraMCP Request Failed: {exc}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    except Exception as e:
        error_message = f"Unexpected error calling GhidraMCP: {e}"
        logger.exception(error_message) # Log full traceback for unexpected errors
        return {"status": "error", "message": error_message}

# --- Ghidra Functions (Not Tools directly, will be wrapped) ---

# --- Project and Binary Management Functions ---

def ghidra_list_projects() -> Dict[str, Any]:
    """
    Lists all available Ghidra projects.
    
    Returns:
        A dictionary: {'status': 'success', 'result': ['project1', 'project2', ...]}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'list_projects')

def ghidra_open_project(project_path: str) -> Dict[str, Any]:
    """
    Opens a Ghidra project at the specified path.
    
    Args:
        project_path: The path to the Ghidra project (.gpr file or directory)
        
    Returns:
        A dictionary: {'status': 'success', 'result': 'Project opened successfully'}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('POST', 'open_project', data=project_path)

def ghidra_import_file(file_path: str, analyze: bool = True) -> Dict[str, Any]:
    """
    Imports a binary file directly into Ghidra for analysis.
    
    Args:
        file_path: The path to the binary file to import
        analyze: Whether to automatically run analysis on the imported file (default: True)
        
    Returns:
        A dictionary: {'status': 'success', 'result': 'File imported successfully'}
        or {'status': 'error', 'message': '...'}.
    """
    payload = {"file_path": file_path, "analyze": analyze}
    return _make_ghidra_request('POST', 'import_file', data=payload)

def ghidra_list_programs() -> Dict[str, Any]:
    """
    Lists all programs (binaries) in the currently open Ghidra project.
    
    Returns:
        A dictionary: {'status': 'success', 'result': ['program1', 'program2', ...]}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'list_programs')

def ghidra_open_program(program_name: str) -> Dict[str, Any]:
    """
    Opens a specific program (binary) in the currently open Ghidra project.
    
    Args:
        program_name: The name of the program to open
        
    Returns:
        A dictionary: {'status': 'success', 'result': 'Program opened successfully'}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('POST', 'open_program', data=program_name)

def ghidra_get_current_program() -> Dict[str, Any]:
    """
    Gets information about the currently open program (binary) in Ghidra.
    
    Returns:
        A dictionary: {'status': 'success', 'result': {'name': 'program1', 'path': '/path/to/program1'}}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'get_current_program')

# --- Existing Analysis Functions ---

def ghidra_list_functions() -> Dict[str, Any]:
    """
    Lists all functions currently loaded in the Ghidra project.
    Connects to the GhidraMCP server running within Ghidra.
    Returns a dictionary: {'status': 'success', 'result': ['func1 (0x...)', 'func2 (0x...)']}
    or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('list_functions')

def ghidra_decompile_function_by_name(function_name: str) -> Dict[str, Any]:
    """
    Decompiles the specified function by its exact name.
    Use this when you know the function's name.
    Connects to the GhidraMCP server running within Ghidra.
    Args:
        function_name: The exact name of the function to decompile (e.g., 'main', 'calculate_checksum').
    Returns:
        A dictionary: {'status': 'success', 'result': '<decompiled C code>'}
        or {'status': 'error', 'message': '...'}.
    """
    # GhidraMCP /decompile expects the name in the raw POST body
    return _make_ghidra_request('POST', 'decompile', data=function_name)

def ghidra_decompile_function_by_address(address: str) -> Dict[str, Any]:
    """
    Decompiles the function located at the specified memory address.
    Use this when you have the starting address of the function.
    Connects to the GhidraMCP server running within Ghidra.
    Args:
        address: The memory address (e.g., '0x401000', '1000h').
    Returns:
        A dictionary: {'status': 'success', 'result': '<decompiled C code>'}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'decompile_function', params={'address': address})

def ghidra_rename_function_by_address(function_address: str, new_name: str) -> Dict[str, Any]:
    """
    Renames the function located at the given address.
    Connects to the GhidraMCP server running within Ghidra.
    Args:
        function_address: The starting address of the function to rename (e.g., '0x401500').
        new_name: The desired new name for the function (e.g., 'process_network_packet').
    Returns:
        A dictionary indicating success or failure: {'status': 'success', 'result': 'OK'}
        or {'status': 'error', 'message': '...'}.
    """
    payload = {"function_address": function_address, "new_name": new_name}
    return _make_ghidra_request('POST', 'rename_function_by_address', data=payload)

def ghidra_set_decompiler_comment(address: str, comment: str) -> Dict[str, Any]:
    """
    Sets or replaces a comment at a specific address within the Decompiler (pseudocode) view.
    Connects to the GhidraMCP server running within Ghidra.
    Args:
        address: The address within a function's pseudocode where the comment should be placed (e.g., '0x40151a').
        comment: The text of the comment to add.
    Returns:
        A dictionary indicating success or failure: {'status': 'success', 'result': 'OK'}
        or {'status': 'error', 'message': '...'}.
    """
    payload = {"address": address, "comment": comment}
    return _make_ghidra_request('POST', 'set_decompiler_comment', data=payload)

def ghidra_set_disassembly_comment(address: str, comment: str) -> Dict[str, Any]:
    """
    Sets or replaces a comment at a specific address within the Listing (disassembly) view.
    Connects to the GhidraMCP server running within Ghidra.
    Args:
        address: The address in the disassembly where the comment should be placed (e.g., '0x40151f').
        comment: The text of the comment to add.
    Returns:
        A dictionary indicating success or failure: {'status': 'success', 'result': 'OK'}
        or {'status': 'error', 'message': '...'}.
    """
    payload = {"address": address, "comment": comment}
    return _make_ghidra_request('POST', 'set_disassembly_comment', data=payload)

def ghidra_get_current_address() -> Dict[str, Any]:
    """
    Gets the memory address currently selected or highlighted by the user in the Ghidra UI.
    Connects to the GhidraMCP server running within Ghidra.
    Returns:
        A dictionary: {'status': 'success', 'result': '0x...'}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'get_current_address')

def ghidra_get_current_function() -> Dict[str, Any]:
    """
    Gets the name or address of the function currently selected or containing the cursor in the Ghidra UI.
    Connects to the GhidraMCP server running within Ghidra.
    Returns:
        A dictionary: {'status': 'success', 'result': 'function_name (0x...)'}
        or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'get_current_function')

# --- Potential Future Tools (Add implementations as needed) ---
# def ghidra_search_strings(pattern: str) -> Dict[str, Any]: ...
# def ghidra_get_references_to(address: str) -> Dict[str, Any]: ...
# def ghidra_rename_variable(...) -> Dict[str, Any]: ...