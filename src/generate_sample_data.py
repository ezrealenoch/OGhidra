#!/usr/bin/env python3
"""
Generate sample data for testing the memory system.
"""

import os
import random
import argparse
import logging
import sys
from datetime import datetime, timedelta

from config import BridgeConfig
from memory_manager import MemoryManager
from memory_health import run_health_check

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Sample data for generating realistic sessions
SAMPLE_TASKS = [
    "Analyze the main function to understand the program's initialization flow",
    "Find all cryptographic functions in the binary",
    "Identify functions that handle user input",
    "Locate potential buffer overflow vulnerabilities in string handling functions",
    "Trace the execution flow from the entry point to the GUI initialization",
    "Analyze how user authentication is implemented",
    "Identify functions related to network communication",
    "Find and examine error handling routines",
    "Locate where configuration files are parsed",
    "Analyze memory allocation patterns for potential memory leaks",
    "Identify functions that process command-line arguments",
    "Find where program updates are checked and downloaded",
    "Trace the data flow for sensitive user information",
    "Analyze how the program handles file operations",
    "Identify functions related to database interactions"
]

SAMPLE_TOOLS = [
    {"name": "list_functions", "params": {}},
    {"name": "list_imports", "params": {"offset": 0, "limit": 100}},
    {"name": "list_exports", "params": {"offset": 0, "limit": 50}},
    {"name": "list_segments", "params": {"offset": 0, "limit": 20}},
    {"name": "decompile_function", "params": {"name": "main"}},
    {"name": "decompile_function", "params": {"name": "initialize"}},
    {"name": "decompile_function", "params": {"name": "parse_config"}},
    {"name": "decompile_function", "params": {"name": "handle_request"}},
    {"name": "decompile_function_by_address", "params": {"address": "0x1400120"}},
    {"name": "decompile_function_by_address", "params": {"address": "0x1400340"}},
    {"name": "search_functions_by_name", "params": {"query": "crypt", "offset": 0, "limit": 20}},
    {"name": "search_functions_by_name", "params": {"query": "auth", "offset": 0, "limit": 20}},
    {"name": "search_functions_by_name", "params": {"query": "parse", "offset": 0, "limit": 20}},
    {"name": "rename_function", "params": {"old_name": "FUN_140001250", "new_name": "initialize_crypto"}},
    {"name": "rename_function", "params": {"old_name": "FUN_140001400", "new_name": "process_user_input"}},
    {"name": "rename_function_by_address", "params": {"function_address": "0x1400120", "new_name": "handle_auth"}}
]

RESULT_PREVIEWS = [
    "Found 132 functions in the binary",
    "Successfully decompiled function with 5 parameters and 12 local variables",
    "Renamed function successfully",
    "Found 8 matches for the query",
    "No matches found for the query",
    "Function contains calls to encryption routines",
    "Function handles file I/O operations",
    "Function appears to process network data",
    "Function contains potential buffer overflow in strcpy usage",
    "Function validates user credentials",
    "Function parses JSON configuration data"
]

def generate_random_session(memory_manager, date_offset=0):
    """
    Generate a random session with realistic tool calls.
    
    Args:
        memory_manager: The MemoryManager instance
        date_offset: Days in the past to generate the session (0 = today)
    
    Returns:
        The session ID of the generated session
    """
    # Select a random task
    task = random.choice(SAMPLE_TASKS)
    
    # Start a new session
    session_id = memory_manager.start_session(task)
    
    # Determine a realistic outcome based on task complexity
    outcome_weights = {
        "success": 0.6,
        "partial_success": 0.25,
        "failure": 0.15
    }
    outcome = random.choices(
        list(outcome_weights.keys()), 
        weights=list(outcome_weights.values())
    )[0]
    
    # Generate a random number of tool calls (2-8)
    num_tools = random.randint(2, 8)
    
    # Generate and log tool calls
    for _ in range(num_tools):
        # Select a random tool and its parameters
        tool_info = random.choice(SAMPLE_TOOLS)
        
        # Determine a realistic status (mostly success, sometimes error)
        status = "success" if random.random() < 0.85 else "error"
        
        # Select a result preview
        result_preview = random.choice(RESULT_PREVIEWS) if status == "success" else "Error: Operation failed"
        
        # Log the tool call
        memory_manager.log_tool_call(
            tool_name=tool_info["name"],
            parameters=tool_info["params"],
            status=status,
            result_preview=result_preview
        )
    
    # Generate a reason based on the outcome
    reason = None
    if outcome == "success":
        reason = f"Successfully analyzed and identified key aspects of {task.split()[1:4]}"
    elif outcome == "partial_success":
        reason = f"Partially completed the analysis but couldn't fully determine {task.split()[1:4]}"
    else:
        reason = f"Failed to complete the analysis due to complexity of {task.split()[1:4]}"
    
    # End the session
    memory_manager.end_session(
        outcome=outcome,
        reason=reason,
        generate_summary=True
    )
    
    # If date_offset is provided, manually adjust the timestamps
    if date_offset > 0:
        session = memory_manager.get_session_by_id(session_id)
        if session:
            # This is a hack since we're directly manipulating the session after it's been saved
            # In a real application, you would have proper methods for this
            offset_time = datetime.now() - timedelta(days=date_offset)
            
            # Create a new session with adjusted dates
            adjusted_session = session
            adjusted_session.start_time = offset_time
            adjusted_session.end_time = offset_time + timedelta(minutes=random.randint(5, 30))
            
            # Manually save this adjusted session, replacing the original
            memory_manager.session_store.save_session(adjusted_session)
    
    return session_id

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate sample data for testing the memory system"
    )
    parser.add_argument(
        "--count", 
        type=int, 
        default=10,
        help="Number of sample sessions to generate (default: 10)"
    )
    parser.add_argument(
        "--time-range", 
        type=int, 
        default=7,
        help="Distribute sessions over this many days in the past (default: 7)"
    )
    parser.add_argument(
        "--enable-vector", 
        action="store_true",
        help="Enable vector embeddings for the generated sessions"
    )
    parser.add_argument(
        "--check-after", 
        action="store_true",
        help="Run a health check after generating data"
    )
    args = parser.parse_args()
    
    # Load configuration
    config = BridgeConfig.from_env()
    
    # Ensure session history is enabled
    config.session_history.enabled = True
    
    # Enable vector embeddings if requested
    if args.enable_vector:
        config.session_history.use_vector_embeddings = True
        logger.info("Vector embeddings enabled for generated sessions")
    
    # Create data directory if needed
    os.makedirs("data", exist_ok=True)
    
    # Initialize memory manager
    memory_manager = MemoryManager(config)
    
    # Generate the specified number of sessions
    logger.info(f"Generating {args.count} sample sessions...")
    for i in range(args.count):
        # Distribute sessions over the specified time range
        if args.time_range > 0:
            date_offset = random.randint(0, args.time_range)
        else:
            date_offset = 0
            
        session_id = generate_random_session(memory_manager, date_offset)
        logger.info(f"Generated session {i+1}/{args.count}: {session_id}")
    
    logger.info(f"Successfully generated {args.count} sample sessions")
    
    # Run health check if requested
    if args.check_after:
        logger.info("Running health check...")
        run_health_check(config, memory_manager)

if __name__ == "__main__":
    main() 