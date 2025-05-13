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
    
    # Memory-specific commands
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
    elif command == 'help':
        print("\n=== Available Commands ===")
        print("exit, quit - Exit the application")
        print("health - Check API health")
        print("vector-store - Display detailed vector store information")
        print("models - List available models")
        print("memory-health - Run detailed memory system health check")
        print("memory-stats - Display memory usage statistics")
        print("memory-clear - Clear all session memory")
        print("memory-vectors-on - Enable vector embeddings for RAG")
        print("memory-vectors-off - Disable vector embeddings")
        print("help - Display this help message")
        print("=========================\n")
        return True
    else:
        # This would be where your regular query processing happens
        # For this implementation, we're just handling the new memory commands
        # Your existing query processing would likely be here
        print(f"Processing query: {command}")
        return True

def interactive_mode(config):
    """
    Run the application in interactive mode.
    
    Args:
        config: The BridgeConfig instance.
    """
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
            command = input("\nQuery (or 'exit', 'quit', 'help', 'health', 'vector-store'): ")
            if not process_interactive_command(command, config, memory_manager):
                break
        except KeyboardInterrupt:
            print("\nExiting interactive mode.")
            break
        except Exception as e:
            print(f"Error processing command: {e}")

def main():
    """Main entry point."""
    args = parse_args()
    
    # Load configuration
    config = BridgeConfig.from_env()
    
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