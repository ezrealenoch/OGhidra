"""
Example usage of the session memory features.
"""

import logging
import sys
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import our modules
from config import BridgeConfig
from memory_manager import MemoryManager
from memory_health import run_health_check

def simulate_ghidra_tool_call(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a call to a Ghidra tool (for demonstration purposes).
    
    Args:
        tool_name: The name of the tool to call.
        params: The parameters to pass to the tool.
        
    Returns:
        A simulated result from the tool.
    """
    logging.info(f"Simulating call to {tool_name} with params: {params}")
    
    # Simulate different tool responses
    if tool_name == "list_functions":
        return {
            "status": "success",
            "data": [
                {"name": "main", "address": "0x1000"},
                {"name": "initialize", "address": "0x1100"},
                {"name": "process_data", "address": "0x1200"}
            ]
        }
    elif tool_name == "decompile_function":
        function_name = params.get("name", "unknown")
        return {
            "status": "success",
            "data": f"void {function_name}() {{\n    // Simulated decompiled code\n    int local_var = 42;\n    call_another_function(local_var);\n}}"
        }
    elif tool_name == "rename_function":
        return {
            "status": "success",
            "data": f"Renamed function from {params.get('old_name')} to {params.get('new_name')}"
        }
    else:
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}"
        }

def main():
    """Run a demonstration of the memory features."""
    # Create a data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Load configuration
    config = BridgeConfig()
    
    # Enable session history and vector embeddings for this demo
    config.session_history.enabled = True
    config.session_history.use_vector_embeddings = True
    
    # Initialize the memory manager
    memory_manager = MemoryManager(config)
    
    # Show the number of existing sessions
    print(f"Found {memory_manager.get_session_count()} existing sessions")
    
    # Start a new session
    user_query = "Analyze the main function and rename any unclear variable names"
    session_id = memory_manager.start_session(user_query)
    print(f"Started new session: {session_id}")
    
    # Simulate some tool calls
    print("\nSimulating tool calls...")
    
    # First tool call: list functions
    tool_name = "list_functions"
    params = {}
    result = simulate_ghidra_tool_call(tool_name, params)
    
    # Log the tool call
    memory_manager.log_tool_call(
        tool_name=tool_name,
        parameters=params,
        status="success" if result["status"] == "success" else "error",
        result_preview=f"Found {len(result['data'])} functions" if result["status"] == "success" else result["message"]
    )
    
    # Second tool call: decompile function
    tool_name = "decompile_function"
    params = {"name": "main"}
    result = simulate_ghidra_tool_call(tool_name, params)
    
    # Log the tool call
    memory_manager.log_tool_call(
        tool_name=tool_name,
        parameters=params,
        status="success" if result["status"] == "success" else "error",
        result_preview="Decompiled main function with local_var"
    )
    
    # Third tool call: rename function
    tool_name = "rename_function"
    params = {"old_name": "local_var", "new_name": "configuration_value"}
    result = simulate_ghidra_tool_call(tool_name, params)
    
    # Log the tool call
    memory_manager.log_tool_call(
        tool_name=tool_name,
        parameters=params,
        status="success" if result["status"] == "success" else "error",
        result_preview=result["data"] if result["status"] == "success" else result["message"]
    )
    
    # End the session with success
    completed_session_id = memory_manager.end_session(
        outcome="success",
        reason="Successfully analyzed and renamed variables in main function",
        generate_summary=True
    )
    print(f"Completed session: {completed_session_id}")
    
    # Start another session
    user_query = "Find all cryptographic functions in the binary"
    session_id = memory_manager.start_session(user_query)
    print(f"\nStarted new session: {session_id}")
    
    # Simulate a tool call
    tool_name = "search_functions_by_name"
    params = {"query": "crypt"}
    result = {"status": "success", "data": "No functions found"}
    
    # Log the tool call
    memory_manager.log_tool_call(
        tool_name=tool_name,
        parameters=params,
        status="success",
        result_preview="No functions with 'crypt' in the name"
    )
    
    # End the session with failure
    completed_session_id = memory_manager.end_session(
        outcome="failure",
        reason="Could not find any cryptographic functions",
        generate_summary=True
    )
    print(f"Completed session: {completed_session_id}")
    
    # Now, let's demonstrate RAG capabilities
    print("\nDemonstrating RAG capabilities...")
    new_query = "How do I rename variables in the main function?"
    similar_sessions = memory_manager.get_similar_sessions(new_query)
    
    print(f"Query: {new_query}")
    print(f"Found {len(similar_sessions)} similar sessions:")
    
    for i, session in enumerate(similar_sessions):
        print(f"\n{i+1}. Session: {session['session_id']}")
        print(f"   Task: {session['user_task']}")
        print(f"   Similarity: {session['similarity']:.4f}")
        print(f"   Outcome: {session['outcome']}")
        if session['summary']:
            print(f"   Summary: {session['summary']}")
    
    # Show some statistics
    recent_sessions = memory_manager.get_recent_sessions(2)
    print(f"\nRecent sessions ({len(recent_sessions)}):")
    for session in recent_sessions:
        print(f"- {session.session_id}: {session.user_task_description} (Outcome: {session.outcome})")
    
    successful_sessions = memory_manager.get_successful_sessions()
    print(f"\nSuccessful sessions ({len(successful_sessions)}):")
    for session in successful_sessions:
        print(f"- {session.session_id}: {session.user_task_description}")
    
    print("\nMemory feature demonstration complete!")
    
    # Run a health check to show system status
    print("\nRunning memory system health check...\n")
    run_health_check(config, memory_manager)

if __name__ == "__main__":
    main() 