#!/usr/bin/env python3
"""
GhidraMCP API Server
This module provides a server implementation for the GhidraMCP API.
It implements the functions defined in the function_signatures.json file.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Path to the function signatures file
FUNCTION_SIGNATURES_PATH = os.path.join("ghidra_knowledge_cache", "function_signatures.json")

# Sample data for demonstration
SAMPLE_DATA = {
    "functions": {},
    "imports": ["ImportFunc1", "ImportFunc2", "ImportFunc3"],
    "exports": ["ExportFunc1", "ExportFunc2", "ExportFunc3"],
    "segments": ["Segment1: 0x1000-0x2000", "Segment2: 0x3000-0x4000"],
    "current_function": "FUN_140001030",
    "current_address": "0x140001030"
}

# Load real function data using the existing /methods endpoint
def load_functions_from_api():
    """
    Load function data from the existing API endpoint.
    
    Returns:
        Dict: Mapping of function names to mocked decompiled code
    """
    import requests
    try:
        response = requests.get("http://localhost:8080/methods")
        functions = response.text.strip().split('\n')
        
        # Create a dictionary with function names as keys and mocked decompiled code as values
        function_data = {}
        for func in functions:
            # Extract address if available in function name (e.g., FUN_140001030)
            address = func.split('_')[1] if '_' in func else None
            
            # Generate mock decompiled code
            func_code = f"""
            // Decompiled code for function {func}
            // Address: {address if address else "unknown"}
            
            undefined4 {func}(int param_1, char *param_2) {{
                int local_10;
                
                for (local_10 = 0; local_10 < param_1; local_10 = local_10 + 1) {{
                    // Sample decompiled code
                    if (param_2[local_10] == '\\0') break;
                    param_2[local_10] = param_2[local_10] + 1;
                }}
                
                return param_1;
            }}
            """
            function_data[func] = func_code
        
        return function_data
    except Exception as e:
        logger.error(f"Error loading functions from API: {e}")
        # Return some default functions if API fails
        return {
            "FUN_140001000": "undefined4 FUN_140001000() { return 0; }",
            "FUN_140001100": "undefined4 FUN_140001100() { return 1; }",
            "main": "int main() { return 0; }"
        }

# Load real methods from the API
SAMPLE_DATA["functions"] = load_functions_from_api()

# Load function signatures
def load_function_signatures():
    """
    Load function signatures from JSON file.
    
    Returns:
        Dict: Function signatures configuration
    """
    try:
        with open(FUNCTION_SIGNATURES_PATH, "r") as f:
            return json.load(f)["function_signatures"]
    except Exception as e:
        logger.error(f"Error loading function signatures: {e}")
        return {}

FUNCTION_SIGNATURES = load_function_signatures()

@app.route("/", methods=["GET"])
def index():
    """Return API documentation."""
    function_list = list(FUNCTION_SIGNATURES.keys())
    endpoints = [
        {"endpoint": "/", "description": "API documentation"},
        {"endpoint": "/methods", "description": "List all function names"},
        {"endpoint": "/method/<name>", "description": "Decompile a function by name"},
        {"endpoint": "/address/<address>", "description": "Decompile a function by address"},
        {"endpoint": "/rename", "description": "Rename a function (POST)"},
        {"endpoint": "/functions", "description": "List all functions"},
        {"endpoint": "/functions/search", "description": "Search functions by name"},
        {"endpoint": "/imports", "description": "List imports"},
        {"endpoint": "/exports", "description": "List exports"},
        {"endpoint": "/segments", "description": "List memory segments"},
        {"endpoint": "/current/function", "description": "Get current function"},
        {"endpoint": "/current/address", "description": "Get current address"},
        {"endpoint": "/bytes/<address>/<length>", "description": "Get raw bytes at address"},
        {"endpoint": "/labels", "description": "Get all labels"},
        {"endpoint": "/structures", "description": "Get data structures"}
    ]
    
    return jsonify({
        "api": "GhidraMCP API",
        "version": "1.0.0",
        "supported_functions": function_list,
        "endpoints": endpoints
    })

@app.route("/methods", methods=["GET"])
def get_methods():
    """
    Get a list of all function names.
    
    Returns:
        Text response with function names
    """
    # Proxy to the existing API endpoint
    import requests
    try:
        response = requests.get("http://localhost:8080/methods")
        return Response(response.text, mimetype="text/plain")
    except Exception as e:
        logger.error(f"Error getting methods from API: {e}")
        # Fall back to our sample data
        return "\n".join(SAMPLE_DATA["functions"].keys())

@app.route("/method/<n>", methods=["GET"])
def decompile_function(n):
    """
    Decompile a function by name.
    
    Args:
        n: Function name
        
    Returns:
        Decompiled function code
    """
    if n in SAMPLE_DATA["functions"]:
        return Response(SAMPLE_DATA["functions"][n], mimetype="text/plain")
    else:
        return Response(f"// Function '{n}' not found", status=404)

@app.route("/address/<address>", methods=["GET"])
def decompile_function_by_address(address):
    """
    Decompile a function by address.
    
    Args:
        address: Function address
        
    Returns:
        Decompiled function code
    """
    # Find function with matching address in the name (e.g., FUN_140001030)
    for func_name, func_code in SAMPLE_DATA["functions"].items():
        if f"_{address}" in func_name:
            return Response(func_code, mimetype="text/plain")
    
    # If no function found, return a mock decompiled function
    mock_func = f"""
    // Decompiled code for function at address {address}
    
    undefined4 FUN_{address}(int param_1, char *param_2) {{
        int local_10;
        
        for (local_10 = 0; local_10 < param_1; local_10 = local_10 + 1) {{
            // Mock decompiled code
            if (param_2[local_10] == '\\0') break;
            param_2[local_10] = param_2[local_10] + 1;
        }}
        
        return param_1;
    }}
    """
    return Response(mock_func, mimetype="text/plain")

@app.route("/rename", methods=["POST"])
def rename_function():
    """
    Rename a function.
    
    Request body:
        - old_name: Current function name
        - new_name: New function name
        OR
        - function_address: Function address
        - new_name: New function name
        
    Returns:
        Success message
    """
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if "old_name" in data and "new_name" in data:
        old_name = data["old_name"]
        new_name = data["new_name"]
        
        if old_name in SAMPLE_DATA["functions"]:
            # Move the function code to the new name
            SAMPLE_DATA["functions"][new_name] = SAMPLE_DATA["functions"][old_name]
            del SAMPLE_DATA["functions"][old_name]
            return jsonify({"success": f"Function '{old_name}' renamed to '{new_name}'"})
        else:
            return jsonify({"error": f"Function '{old_name}' not found"}), 404
    
    elif "function_address" in data and "new_name" in data:
        address = data["function_address"]
        new_name = data["new_name"]
        
        # Find function with matching address in the name (e.g., FUN_140001030)
        found = False
        for func_name in list(SAMPLE_DATA["functions"].keys()):
            if f"_{address}" in func_name:
                # Move the function code to the new name
                SAMPLE_DATA["functions"][new_name] = SAMPLE_DATA["functions"][func_name]
                del SAMPLE_DATA["functions"][func_name]
                found = True
                break
        
        if found:
            return jsonify({"success": f"Function at address '{address}' renamed to '{new_name}'"})
        else:
            return jsonify({"error": f"Function at address '{address}' not found"}), 404
    
    else:
        return jsonify({"error": "Invalid data provided"}), 400

@app.route("/functions", methods=["GET"])
def list_functions():
    """
    List all functions.
    
    Returns:
        Array of function names
    """
    return jsonify(list(SAMPLE_DATA["functions"].keys()))

@app.route("/functions/search", methods=["GET"])
def search_functions_by_name():
    """
    Search functions by name substring.
    
    Query parameters:
        - query: Search query
        - offset: Offset to start from (default: 0)
        - limit: Maximum number of results (default: 100)
        
    Returns:
        Array of matching function names
    """
    query = request.args.get("query", "")
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 100))
    
    matching_functions = [
        func_name for func_name in SAMPLE_DATA["functions"].keys()
        if query.lower() in func_name.lower()
    ]
    
    # Apply pagination
    paginated_functions = matching_functions[offset:offset + limit]
    
    return jsonify(paginated_functions)

@app.route("/imports", methods=["GET"])
def list_imports():
    """
    List imported symbols.
    
    Query parameters:
        - offset: Offset to start from (default: 0)
        - limit: Maximum number of results (default: 100)
        
    Returns:
        Array of imported symbol names
    """
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 100))
    
    # Apply pagination
    paginated_imports = SAMPLE_DATA["imports"][offset:offset + limit]
    
    return jsonify(paginated_imports)

@app.route("/exports", methods=["GET"])
def list_exports():
    """
    List exported symbols.
    
    Query parameters:
        - offset: Offset to start from (default: 0)
        - limit: Maximum number of results (default: 100)
        
    Returns:
        Array of exported symbol names
    """
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 100))
    
    # Apply pagination
    paginated_exports = SAMPLE_DATA["exports"][offset:offset + limit]
    
    return jsonify(paginated_exports)

@app.route("/segments", methods=["GET"])
def list_segments():
    """
    List memory segments.
    
    Query parameters:
        - offset: Offset to start from (default: 0)
        - limit: Maximum number of results (default: 100)
        
    Returns:
        Array of segment information
    """
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 100))
    
    # Apply pagination
    paginated_segments = SAMPLE_DATA["segments"][offset:offset + limit]
    
    return jsonify(paginated_segments)

@app.route("/current/function", methods=["GET"])
def get_current_function():
    """
    Get the function at the current cursor position.
    
    Returns:
        Current function information
    """
    return jsonify(SAMPLE_DATA["current_function"])

@app.route("/current/address", methods=["GET"])
def get_current_address():
    """
    Get the address at the current cursor position.
    
    Returns:
        Current address
    """
    return jsonify(SAMPLE_DATA["current_address"])

@app.route("/bytes/<address>/<length>", methods=["GET"])
def get_bytes(address, length):
    """
    Get raw bytes at a specific address.
    
    Args:
        address: Memory address
        length: Number of bytes to read
        
    Returns:
        Hexadecimal representation of bytes
    """
    try:
        length = int(length)
    except ValueError:
        return jsonify({"error": "Invalid length"}), 400
    
    # Generate mock bytes data
    byte_data = ""
    for i in range(length):
        # Generate predictable byte based on address and position
        byte_val = (int(address, 16) + i) % 256
        byte_data += f"{byte_val:02x} "
    
    return Response(byte_data.strip(), mimetype="text/plain")

@app.route("/labels", methods=["GET"])
def get_labels():
    """
    Get all labels in the program.
    
    Returns:
        List of labels
    """
    # Generate mock labels from function names
    labels = list(SAMPLE_DATA["functions"].keys())
    
    # Add some additional labels
    labels.extend(["DAT_14000000", "LAB_14000100", "SUB_140002000"])
    
    return Response("\n".join(labels), mimetype="text/plain")

@app.route("/structures", methods=["GET"])
def get_structures():
    """
    Get data structures information.
    
    Returns:
        Data structures information
    """
    # Mock data structures
    structures = """
    struct Point {
        int x;
        int y;
    };
    
    struct Rectangle {
        Point topLeft;
        Point bottomRight;
    };
    
    struct Circle {
        Point center;
        int radius;
    };
    """
    
    return Response(structures.strip(), mimetype="text/plain")

if __name__ == "__main__":
    # Load real function data first
    SAMPLE_DATA["functions"] = load_functions_from_api()
    
    # Start the server
    port = int(os.environ.get("PORT", 8081))
    app.run(host="0.0.0.0", port=port, debug=True)
    
    logger.info(f"Server running on port {port}") 