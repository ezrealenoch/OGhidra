#!/usr/bin/env python3
"""
Main entry point for the Ollama-GhidraMCP Bridge application.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Import after loading environment variables
from src.config import BridgeConfig
from src.bridge import Bridge
from src.ollama_client import OllamaClient

def print_header():
    """Print the application header."""
    width = 70
    header = [
        "OGhidra - Simplified Three-Phase Architecture",
        "------------------------------------------",
        "",
        "1. Planning Phase: Create a plan for addressing the query",
        "2. Tool Calling Phase: Execute tools to gather information",
        "3. Analysis Phase: Analyze results and provide answers",
        "",
        "For more information, see README-ARCHITECTURE.md"
    ]
    
    print('╔' + '═' * (width - 2) + '╗')
    for line in header:
        padding = (width - 2 - len(line))
        left_padding = padding // 2
        right_padding = padding - left_padding
        print('║' + ' ' * left_padding + line + ' ' * right_padding + '║')
    print('╚' + '═' * (width - 2) + '╝')

def run_interactive_mode(bridge, config):
    """Run the bridge in interactive mode."""
    print("Ollama-GhidraMCP Bridge (Interactive Mode)")
    print(f"Default model: {config.ollama.model}")
    
    ollama_client = OllamaClient(config.ollama)
    
    while True:
        # Get user input
        try:
            user_input = input("Query (or 'exit', 'quit', 'help', 'health', 'tools', 'models', 'vector-store'): ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
            
        if user_input.lower() in ('exit', 'quit'):
            break
        elif user_input.lower() == 'health':
            # Check Ollama and GhidraMCP health
            ollama_health = ollama_client.check_health()
            ghidra_health = bridge.ghidra.check_health()
            
            print("\n=== Health Check ===")
            print(f"Ollama API: {'OK' if ollama_health else 'NOT OK'}")
            print(f"GhidraMCP API: {'OK' if ghidra_health else 'NOT OK'}")
            print("====================\n")
            
            # Display vector store information if CAG is enabled
            if bridge.enable_cag and bridge.cag_manager:
                print("\n=== Vector Store Information ===")
                # Get vector store info from bridge
                try:
                    vector_store_enabled = config.session_history.use_vector_embeddings if hasattr(config, 'session_history') else False
                    print(f"Vector embeddings: {'Enabled ✅' if vector_store_enabled else 'Disabled ❌'}")
                    
                    if vector_store_enabled and hasattr(bridge, 'memory_manager') and bridge.memory_manager is not None:
                        mm = bridge.memory_manager
                        if mm.vector_store:
                            vector_count = mm.vector_store.vectors.shape[0] if (hasattr(mm.vector_store, 'vectors') and 
                                                                           mm.vector_store.vectors is not None) else 0
                            print(f"Vectors available: {'Yes ✅' if vector_count > 0 else 'No ❌'}")
                            print(f"Vector count: {vector_count}")
                            
                            if vector_count > 0:
                                print(f"Vector dimension: {mm.vector_store.vectors.shape[1]}")
                                # Calculate mean norm
                                import numpy as np
                                norms = np.linalg.norm(mm.vector_store.vectors, axis=1)
                                print(f"Mean vector norm: {float(np.mean(norms)):.4f}")
                                
                                # Show session IDs if available
                                if hasattr(mm.vector_store, 'get_session_ids'):
                                    session_ids = mm.vector_store.get_session_ids()
                                    if session_ids:
                                        print(f"\nStored Session IDs ({len(session_ids)}):")
                                        for i, sid in enumerate(session_ids[:5]):  # Show first 5
                                            print(f"  {i+1}. {sid}")
                                        if len(session_ids) > 5:
                                            print(f"  ... and {len(session_ids) - 5} more")
                except Exception as e:
                    print(f"Error displaying vector store info: {e}")
                
                print("===============================\n")
            continue
        elif user_input.lower() == 'vector-store':
            # Add dedicated command for vector store inspection
            print("\n=== Vector Store Information ===")
            # Get vector store info from bridge
            try:
                vector_store_enabled = config.session_history.use_vector_embeddings if hasattr(config, 'session_history') else False
                print(f"Vector embeddings: {'Enabled ✅' if vector_store_enabled else 'Disabled ❌'}")
                
                if vector_store_enabled and hasattr(bridge, 'memory_manager') and bridge.memory_manager is not None:
                    mm = bridge.memory_manager
                    if mm.vector_store:
                        vector_count = mm.vector_store.vectors.shape[0] if (hasattr(mm.vector_store, 'vectors') and 
                                                                       mm.vector_store.vectors is not None) else 0
                        print(f"Vectors available: {'Yes ✅' if vector_count > 0 else 'No ❌'}")
                        print(f"Vector count: {vector_count}")
                        
                        if vector_count > 0:
                            print(f"Vector dimension: {mm.vector_store.vectors.shape[1]}")
                            # Calculate mean norm
                            import numpy as np
                            norms = np.linalg.norm(mm.vector_store.vectors, axis=1)
                            print(f"Mean vector norm: {float(np.mean(norms)):.4f}")
                            
                            # Show session IDs if available
                            if hasattr(mm.vector_store, 'get_session_ids'):
                                session_ids = mm.vector_store.get_session_ids()
                                if session_ids:
                                    print(f"\nStored Session IDs ({len(session_ids)}):")
                                    for i, sid in enumerate(session_ids):
                                        print(f"  {i+1}. {sid}")
            except Exception as e:
                print(f"Error displaying vector store info: {e}")
            
            print("===============================\n")
            continue
        elif user_input.lower() == 'models':
            # List available models
            models = ollama_client.list_models()
            
            print("\n=== Available Models ===")
            for model in models:
                print(f"- {model}")
            print("========================\n")
            continue
        elif user_input.lower() == 'tools':
            # Display all available Ghidra tools and their parameters
            print("\n=== Available Ghidra Tools ===")
            
            # Import the necessary classes
            try:
                from src.ghidra_client import GhidraMCPClient
                
                # Create a temporary client instance to get its methods
                client = bridge.ghidra if hasattr(bridge, 'ghidra') else GhidraMCPClient(config.ghidra)
                
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
            continue
        elif user_input.lower() == 'cag':
            # Show CAG status
            if bridge.enable_cag and bridge.cag_manager:
                info = bridge.cag_manager.get_debug_info()
                print("\n=== CAG Status ===")
                print(f"CAG Enabled: {info['enabled']}")
                print(f"Knowledge Cache Enabled: {info['knowledge_cache_enabled']}")
                print(f"Session Cache Enabled: {info['session_cache_enabled']}")
                print(f"Token Limit: {info['token_limit']}")
                print("=================\n")
            else:
                print("\nCAG is disabled. Enable it with CAG_ENABLED=true in your .env file.\n")
            continue
        elif user_input.lower() == 'help':
            print("\n=== Available Commands ===")
            print("exit, quit - Exit the application")
            print("health - Check API health")
            print("vector-store - Display detailed vector store information")
            print("models - List available models")
            print("tools - List all available Ghidra tools with parameters")
            print("run-tool tool_name(param1='value1', param2='value2') - Execute a specific Ghidra tool directly")
            print("analyze-function [address] - Analyze current function or specified address")
            print("cag - Display Context-Aware Generation status")
            print("help - Display this help message")
            print("=========================\n")
            continue
        elif user_input.lower().startswith('run-tool '):
            # Execute a specific tool directly
            tool_str = user_input[9:].strip()  # Remove 'run-tool ' prefix
            
            try:
                # Parse the tool name and parameters
                if '(' not in tool_str or ')' not in tool_str:
                    print("Invalid format. Use: run-tool tool_name(param1='value1', param2='value2')")
                    continue
                    
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
                
                # Get the client
                client = bridge.ghidra
                
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
                
            continue
        elif user_input.lower() == 'analyze-function' or user_input.lower().startswith('analyze-function '):
            # Shortcut command to analyze a function
            try:
                # Extract address if provided (e.g., "analyze-function 140001000")
                address = None
                if user_input.lower().startswith('analyze-function '):
                    address = user_input[16:].strip()
                    if not address:
                        address = None
                
                print(f"\nExecuting: analyze_function({f'address=\"{address}\"' if address else ''})")
                result = bridge.ghidra.analyze_function(address)
                
                print("\n============================================================")
                print(f"Results from analyze_function:")
                print("============================================================")
                print(result)
                print("============================================================\n")
            except Exception as e:
                print(f"Error analyzing function: {str(e)}")
                
            continue
        elif not user_input.strip():
            continue
            
        # Process the query
        try:
            result = bridge.process_query(user_input)
            # Print the result
            print(result)
        except Exception as e:
            print(f"Error processing query: {str(e)}")

def main():
    """Main entry point for the Ollama-GhidraMCP Bridge CLI."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Bridge between Ollama and GhidraMCP for binary analysis")
    parser.add_argument("--interactive", "-i", action="store_true", help="Enable interactive mode")
    parser.add_argument("--query", "-q", type=str, help="Single query to execute (non-interactive mode)")
    parser.add_argument("--include-capabilities", "-c", action="store_true", 
                       help="Include tool capabilities in the prompt (may use more tokens)")
    parser.add_argument("--disable-cag", action="store_true", 
                       help="Disable Cache-Augmented Generation (CAG)")
    
    args = parser.parse_args()
    
    # Check if we have a query or interactive mode
    if not args.interactive and not args.query:
        parser.print_help()
        return
    
    # Load configuration from environment
    config = BridgeConfig.from_env()
    
    # Override CAG settings from command line if specified
    if args.disable_cag:
        config.cag_enabled = False
    
    # Create the bridge
    bridge = Bridge(
        config=config, 
        include_capabilities=args.include_capabilities,
        max_agent_steps=config.max_steps,
        enable_cag=config.cag_enabled
    )
    
    # Print header
    print_header()
    
    if args.interactive:
        run_interactive_mode(bridge, config)
    else:
        # Single query mode
        result = bridge.process_query(args.query)
        print(result)

if __name__ == "__main__":
    sys.exit(main()) 