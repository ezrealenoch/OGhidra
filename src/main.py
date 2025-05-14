#!/usr/bin/env python3
"""
Main entry point for the Ollama-GhidraMCP Bridge.
"""

import argparse
import logging
import sys
import os

from config import BridgeConfig
from memory_manager import MemoryManager
from memory_health import run_health_check, MemoryHealthCheck

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ollama-GhidraMCP Bridge - Connect Ollama LLMs to Ghidra via GhidraMCP"
    )
    
    parser.add_argument(
        "--check-memory", 
        action="store_true",
        help="Run a health check on the memory system and display the results"
    )
    
    parser.add_argument(
        "--clear-memory", 
        action="store_true",
        help="Clear all session memory (USE WITH CAUTION)"
    )
    
    parser.add_argument(
        "--enable-vector-embeddings", 
        action="store_true",
        help="Enable vector embeddings for RAG capabilities"
    )
    
    parser.add_argument(
        "--disable-vector-embeddings", 
        action="store_true",
        help="Disable vector embeddings to save resources"
    )
    
    parser.add_argument(
        "--disable-cag", 
        action="store_true",
        help="Disable Context-Aware Generation (CAG)"
    )
    
    parser.add_argument(
        "--memory-stats", 
        action="store_true",
        help="Display simple statistics about memory usage and exit"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start in interactive mode"
    )
    
    return parser.parse_args()

def display_memory_stats(memory_manager):
    """Display simple memory statistics."""
    session_count = memory_manager.get_session_count()
    recent_sessions = memory_manager.get_recent_sessions(5)
    successful_sessions = memory_manager.get_successful_sessions()
    
    print("\n" + "="*50)
    print(" MEMORY STATISTICS")
    print("="*50)
    print(f"Total sessions: {session_count}")
    print(f"Successful sessions: {len(successful_sessions)}")
    
    if recent_sessions:
        print("\nRecent sessions:")
        for i, session in enumerate(recent_sessions):
            print(f"{i+1}. {session.user_task_description[:60]}{'...' if len(session.user_task_description) > 60 else ''}")
            print(f"   Outcome: {session.outcome}, Tools used: {len(session.tool_calls)}")
            if session.session_summary:
                print(f"   Summary: {session.session_summary[:100]}{'...' if len(session.session_summary) > 100 else ''}")
            print()
    
    print("="*50 + "\n")

def toggle_vector_embeddings(config, enable=True):
    """Toggle vector embeddings on or off."""
    config.session_history.use_vector_embeddings = enable
    status = "enabled" if enable else "disabled"
    logger.info(f"Vector embeddings {status}")
    print(f"\nVector embeddings are now {status}.\n")
    return config

def process_interactive_command(command, config, memory_manager):
    """
    Process interactive commands.
    
    Args:
        command: The command string from the user.
        config: The BridgeConfig instance.
        memory_manager: The MemoryManager instance.
        
    Returns:
        bool: True to continue, False to exit.
    """
    command = command.strip().lower()
    
    if command in ['exit', 'quit']:
        return False
    elif command == 'health':
        print("\n=== API Health Check ===")
        try:
            # This is a placeholder - you would need to implement your actual API health checks here
            # For example, pinging the Ollama and GhidraMCP APIs
            print("Ollama API: OK") # Replace with actual check
            print("GhidraMCP API: OK") # Replace with actual check
        except Exception as e:
            print(f"API health check failed: {e}")
        print("========================\n")
        
        # Now run the memory health check
        run_health_check(config, memory_manager)
        
        # Also show the vector store information
        print("\n=== Vector Store Information ===")
        health_checker = MemoryHealthCheck(config, memory_manager)
        vector_info = health_checker.check_vector_store()
        
        print(f"Vector embeddings: {'Enabled ✅' if vector_info['enabled'] else 'Disabled ❌'}")
        
        if vector_info['enabled']:
            print(f"Embedding model: {vector_info['embedding_model']}")
            print(f"Vectors available: {'Yes ✅' if vector_info['vectors_available'] else 'No ❌'}")
            
            if vector_info['vectors_available']:
                print(f"Vector count: {vector_info['vector_count']}")
                print(f"Vector dimension: {vector_info['vector_dimension']}")
                print(f"Mean vector norm: {vector_info['vector_norm_mean']:.4f}")
                
                # Display all session IDs in vector store
                session_ids = vector_info.get('session_ids', [])
                if session_ids:
                    print(f"\nStored Session IDs ({len(session_ids)}):")
                    for i, sid in enumerate(session_ids):
                        print(f"  {i+1}. {sid}")
                
                # Display sample similarity matrix if available
                if 'sample_similarity_matrix' in vector_info:
                    print("\nSample Vector Similarity Matrix:")
                    matrix = vector_info['sample_similarity_matrix']
                    for i, row in enumerate(matrix):
                        print(f"  {i}: {' '.join([f'{val:.2f}' for val in row])}")
        
        print("===============================\n")
        return True
    elif command == 'vector-store':
        # Add a dedicated command for vector store inspection
        print("\n=== Vector Store Information ===")
        health_checker = MemoryHealthCheck(config, memory_manager)
        vector_info = health_checker.check_vector_store()
        
        print(f"Vector embeddings: {'Enabled ✅' if vector_info['enabled'] else 'Disabled ❌'}")
        
        if vector_info['enabled']:
            print(f"Embedding model: {vector_info['embedding_model']}")
            print(f"Vectors available: {'Yes ✅' if vector_info['vectors_available'] else 'No ❌'}")
            
            if vector_info['vectors_available']:
                print(f"Vector count: {vector_info['vector_count']}")
                print(f"Vector dimension: {vector_info['vector_dimension']}")
                print(f"Mean vector norm: {vector_info['vector_norm_mean']:.4f}")
                
                # Display all session IDs in vector store
                session_ids = vector_info.get('session_ids', [])
                if session_ids:
                    print(f"\nStored Session IDs ({len(session_ids)}):")
                    for i, sid in enumerate(session_ids):
                        print(f"  {i+1}. {sid}")
                
                # Display sample similarity matrix if available
                if 'sample_similarity_matrix' in vector_info:
                    print("\nSample Vector Similarity Matrix:")
                    matrix = vector_info['sample_similarity_matrix']
                    for i, row in enumerate(matrix):
                        print(f"  {i}: {' '.join([f'{val:.2f}' for val in row])}")
        
        print("===============================\n")
        return True
    elif command == 'models':
        # This is a placeholder - you would need to implement your actual model listing logic
        print("\n=== Available Models ===")
        print("gemma3:27b (current)")
        print("llama3.1:8b")
        print("mistral:7b")
        print("======================\n")
        return True
    elif command == 'tools':
        # Display all available Ghidra tools and their parameters
        print("\n=== Available Ghidra Tools ===")
        
        # Import the tools from config
        try:
            from src.ghidra_client import GhidraMCPClient
            
            # Create a temporary client instance to get its methods
            client = GhidraMCPClient(config.ghidra)
            
            # Get all public methods (excluding those starting with _)
            tools = [name for name in dir(client) if not name.startswith('_') and callable(getattr(client, name))]
            
            # Count the tools and provide a summary
            print(f"Found {len(tools)} available tools:\n")
            
            for tool_name in sorted(tools):
                tool_func = getattr(client, tool_name)
                # Get parameter info from function signature
                import inspect
                signature = inspect.signature(tool_func)
                params = []
                for param_name, param in signature.parameters.items():
                    if param_name != 'self':  # Skip the 'self' parameter
                        if param.default is inspect.Parameter.empty:
                            params.append(f"{param_name} (required)")
                        else:
                            default_val = param.default
                            if default_val is None:
                                default_val = "None"
                            params.append(f"{param_name}={default_val}")
                
                # Get docstring if available
                doc = tool_func.__doc__.strip().split('\n')[0] if tool_func.__doc__ else "No description available"
                
                print(f"  {tool_name}({', '.join(params)})")
                print(f"    {doc}")
                print()
                
        except Exception as e:
            print(f"Error loading tools: {str(e)}")
            print(f"Debugging details:")
            print(f"  Exception type: {type(e).__name__}")
            print(f"  Exception traceback:")
            import traceback
            traceback.print_exc()
            
        print("===========================\n")
        return True
    elif command.startswith('run-tool '):
        # Execute a specific tool directly
        tool_str = command[9:].strip()  # Remove 'run-tool ' prefix
        
        try:
            # Parse the tool name and parameters
            if '(' not in tool_str or ')' not in tool_str:
                print("Invalid format. Use: run-tool tool_name(param1='value1', param2='value2')")
                return True
                
            tool_name = tool_str[:tool_str.find('(')].strip()
            params_str = tool_str[tool_str.find('(')+1:tool_str.rfind(')')].strip()
            
            # Parse parameters (simple version, could be enhanced)
            params = {}
            if params_str:
                param_pairs = params_str.split(',')
                for pair in param_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                            
                        params[key] = value
            
            # Import the client and execute the tool
            from src.ghidra_client import GhidraMCPClient
            client = GhidraMCPClient(config.ghidra)
            
            if hasattr(client, tool_name) and callable(getattr(client, tool_name)):
                tool_func = getattr(client, tool_name)
                print(f"\nExecuting: {tool_name}({', '.join([f'{k}=\"{v}\"' for k, v in params.items()])})")
                result = tool_func(**params)
                
                print("\n============================================================")
                print(f"Results from {tool_name}:")
                print("============================================================")
                
                if isinstance(result, list):
                    for i, item in enumerate(result):
                        print(f"  {i+1}. {item}")
                    print(f"Total: {len(result)} items")
                else:
                    print(result)
                print("============================================================\n")
            else:
                print(f"Unknown tool: {tool_name}")
        except Exception as e:
            print(f"Error executing tool: {str(e)}")
            
        return True
    elif command == 'analyze-function' or command.startswith('analyze-function '):
        # Shortcut command to analyze a function
        try:
            from src.ghidra_client import GhidraMCPClient
            client = GhidraMCPClient(config.ghidra)
            
            # Extract address if provided (e.g., "analyze-function 140001000")
            address = None
            if command.startswith('analyze-function '):
                address = command[16:].strip()
                if not address:
                    address = None
            
            print(f"\nExecuting: analyze_function({f'address=\"{address}\"' if address else ''})")
            result = client.analyze_function(address)
            
            print("\n============================================================")
            print(f"Results from analyze_function:")
            print("============================================================")
            print(result)
            print("============================================================\n")
        except Exception as e:
            print(f"Error analyzing function: {str(e)}")
            
        return True
    elif command == 'help':
        print("\n=== Available Commands ===")
        print("exit, quit - Exit the application")
        print("health - Check API health")
        print("vector-store - Display detailed vector store information")
        print("models - List available models")
        print("tools - List all available Ghidra tools with parameters")
        print("run-tool - Execute a specific tool (e.g., run-tool analyze_function(address=\"1400011a8\"))")
        print("analyze-function [address] - Analyze current function or specified address")
        print("memory-health - Run detailed memory system health check")
        print("memory-stats - Display memory usage statistics")
        print("memory-clear - Clear all session memory")
        print("memory-vectors-on - Enable vector embeddings for RAG")
        print("memory-vectors-off - Disable vector embeddings")
        print("help - Display this help message")
        print("=========================\n")
        return True
    elif command in ['memory-health', 'memory-check']:
        print("Running detailed memory system health check...")
        run_health_check(config, memory_manager)
        return True
    elif command == 'memory-stats':
        display_memory_stats(memory_manager)
        return True
    elif command == 'memory-clear':
        print("\nWARNING: This will delete all session history. This action cannot be undone.")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm.upper() == "CONFIRM":
            if memory_manager.clear_all_sessions():
                print("Memory cleared successfully")
            else:
                print("Failed to clear memory")
        else:
            print("Operation cancelled")
        return True
    elif command == 'memory-vectors-on':
        toggle_vector_embeddings(config, True)
        # Reload memory manager to apply changes
        return True
    elif command == 'memory-vectors-off':
        toggle_vector_embeddings(config, False)
        # Reload memory manager to apply changes
        return True
    else:
        # For non-special commands, indicate that we should process it as a regular query
        # The interactive_mode function will handle the actual processing with the bridge
        return True

def interactive_mode(config):
    """
    Run the application in interactive mode.
    
    Args:
        config: The BridgeConfig instance.
    """
    # Import bridge here to avoid circular imports
    from src.bridge import Bridge
    
    # Initialize memory manager
    memory_manager = MemoryManager(config)
    
    print("\n╔════════════════════════════════════════════════════════════════════╗")
    print("║           OGhidra - Simplified Three-Phase Architecture            ║")
    print("║             ------------------------------------------             ║")
    print("║                                                                    ║")
    print("║     1. Planning Phase: Create a plan for addressing the query      ║")
    print("║     2. Tool Calling Phase: Execute tools to gather information     ║")
    print("║       3. Analysis Phase: Analyze results and provide answers       ║")
    print("║                                                                    ║")
    print("║          For more information, see README-ARCHITECTURE.md          ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print("Ollama-GhidraMCP Bridge (Interactive Mode)")
    print(f"Default model: {config.ollama.model}")
    print("Type 'help' for a list of commands.")

    while True:
        try:
            command = input("\nQuery (or 'exit', 'quit', 'help', 'health', 'tools', 'models', 'vector-store', etc.): ")
            
            # Check if this is a special command that should be handled by process_interactive_command
            special_commands = ['exit', 'quit', 'help', 'health', 'vector-store', 'models', 'tools', 
                               'memory-health', 'memory-check', 'memory-stats', 'memory-clear', 
                               'memory-vectors-on', 'memory-vectors-off']
            
            # Also consider commands that start with specific prefixes
            command_prefixes = ['run-tool', 'analyze-function']
            
            # Check if command matches any special command or prefix
            is_special_command = (command.strip().lower() in special_commands or
                                 any(command.strip().lower().startswith(prefix) for prefix in command_prefixes))
            
            if is_special_command:
                if not process_interactive_command(command, config, memory_manager):
                    break
            else:
                # Handle as a regular query to be processed by the bridge
                print(f"Processing query: {command}")
                
                # Initialize the bridge with the current config
                try:
                    bridge = Bridge(
                        config=config,
                        include_capabilities=True,
                        max_agent_steps=config.max_steps
                    )
                except TypeError as e:
                    # Handle case where Bridge constructor parameters have changed
                    print(f"Error initializing Bridge: {e}")
                    print("Trying fallback initialization...")
                    bridge = Bridge(config=config)
                
                # Process the query using the bridge
                try:
                    response = bridge.process_query(command)
                    print("\nResponse:")
                    print(response)
                except Exception as e:
                    print(f"Error processing query with bridge: {e}")
                
        except KeyboardInterrupt:
            print("\nExiting interactive mode.")
            break
        except Exception as e:
            print(f"Error processing command: {e}")

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set log level from arguments or environment
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level
        
    # Configure based on arguments and environment variables
    config = BridgeConfig.from_env() # Load defaults and other env vars first
    
    # Override with command line arguments
    if args.ollama_url:
        config.ollama.base_url = args.ollama_url
    if args.ghidra_url:
        config.ghidra.base_url = args.ghidra_url
    if args.model:
        config.ollama.model = args.model
    if args.mock:
        config.ghidra.mock_mode = True
    
    # Override configuration from command-line arguments
    if args.enable_vector_embeddings:
        config.session_history.use_vector_embeddings = True
        logger.info("Vector embeddings enabled")
    
    if args.disable_vector_embeddings:
        config.session_history.use_vector_embeddings = False
        logger.info("Vector embeddings disabled")
    
    if args.disable_cag:
        config.cag_enabled = False
        logger.info("Context-Aware Generation (CAG) disabled")
    
    # Initialize memory manager
    memory_manager = MemoryManager(config)
    
    # Handle interactive mode
    if args.interactive:
        interactive_mode(config)
        return
    
    # Handle memory-specific commands
    if args.clear_memory:
        print("WARNING: This will delete all session history. This action cannot be undone.")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm.upper() == "CONFIRM":
            if memory_manager.clear_all_sessions():
                print("Memory cleared successfully")
            else:
                print("Failed to clear memory")
        else:
            print("Operation cancelled")
        return
    
    if args.memory_stats:
        display_memory_stats(memory_manager)
        return
    
    if args.check_memory:
        run_health_check(config, memory_manager)
        return
    
    # Initialize the bridge (ensure this uses the potentially updated config)
    bridge = Bridge(
        config=config,
        include_capabilities=args.include_capabilities,
        max_agent_steps=config.max_steps # This should now use the value from .env via config
    )
    
    # Health check for Ollama and GhidraMCP
    # ... rest of the main() function ...

    # Start the main application
    start_bridge(config, memory_manager)

def start_bridge(config, memory_manager):
    """Start the Ollama-GhidraMCP Bridge."""
    # This is a placeholder for the actual bridge startup code
    try:
        logger.info("Starting Ollama-GhidraMCP Bridge")
        logger.info(f"Using Ollama model: {config.ollama.model}")
        logger.info(f"GhidraMCP URL: {config.ghidra.base_url}")
        
        if config.session_history.enabled:
            logger.info(f"Session history enabled, storage path: {config.session_history.storage_path}")
            logger.info(f"Memory system loaded {memory_manager.get_session_count()} sessions")
            
            if config.session_history.use_vector_embeddings:
                vector_count = 0
                if memory_manager.vector_store:
                    vector_count = memory_manager.vector_store.vectors.shape[0] if memory_manager.vector_store.vectors is not None else 0
                logger.info(f"Vector embeddings enabled, {vector_count} vectors loaded")
        
        # Your actual bridge startup code would go here
        print("\nBridge is running. Press Ctrl+C to stop.\n")
        
        # Keep the application running
        try:
            while True:
                # In a real application, you would have your main loop here
                # This is just a placeholder to keep the app running
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down bridge")
    
    except Exception as e:
        logger.exception(f"Error starting bridge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 