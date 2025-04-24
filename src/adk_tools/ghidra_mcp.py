"""
ADK Tools for interacting with the GhidraMCP server.

These tools provide a structured interface for the ADK agent
to call functions within a running Ghidra instance via the GhidraMCP bridge.
"""

import os
import httpx
import logging
from typing import List, Dict, Any, Optional

# Configure basic logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# --- GhidraMCP Configuration ---
GHIDRA_MCP_BASE_URL = os.getenv("GHIDRA_MCP_URL", "http://localhost:8080")
GHIDRA_MCP_TIMEOUT = int(os.getenv("GHIDRA_MCP_TIMEOUT", "60")) # Increased timeout for potentially long operations

# --- Internal Helper Functions ---

def _make_ghidra_request(method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Any] = None) -> Dict[str, Any]:
    """
    Internal helper to make HTTP requests to the GhidraMCP server.

    Args:
        method: HTTP method ('GET' or 'POST').
        endpoint: The API endpoint path.
        params: Dictionary of query parameters for GET requests.
        data: Data payload for POST requests (can be dict or str).

    Returns:
        A dictionary containing the result:
        {'status': 'success', 'result': <parsed_response>} or
        {'status': 'error', 'message': <error_details>}
    """
    url = f"{GHIDRA_MCP_BASE_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'} if isinstance(data, dict) else {}

    try:
        with httpx.Client(timeout=GHIDRA_MCP_TIMEOUT) as client:
            logger.debug(f"Sending {method} to GhidraMCP: {url} | Params: {params} | Data: {data}")

            if method.upper() == 'GET':
                response = client.get(url, params=params or {})
            elif method.upper() == 'POST':
                if isinstance(data, dict):
                    response = client.post(url, json=data, headers=headers)
                elif isinstance(data, str):
                     # GhidraMCP often expects raw string data for POST
                    response = client.post(url, data=data.encode('utf-8'), headers={'Content-Type': 'text/plain'})
                else:
                    raise ValueError("Unsupported POST data type")
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses

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

def ghidra_list_functions() -> Dict[str, Any]:
    """
    Lists all functions currently loaded in the Ghidra project.
    Connects to the GhidraMCP server running within Ghidra.
    Returns a dictionary: {'status': 'success', 'result': ['func1 (0x...)', 'func2 (0x...)']}
    or {'status': 'error', 'message': '...'}.
    """
    return _make_ghidra_request('GET', 'list_functions')

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