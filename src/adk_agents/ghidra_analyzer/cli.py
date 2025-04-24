#!/usr/bin/env python3
"""
Command-line interface for the Ghidra analyzer.
This script allows users to run the Ghidra analyzer with different queries from the command line.
"""

import sys
import argparse
import logging
from .agents import build_ghidra_analyzer_pipeline

def main():
    """Run the Ghidra analyzer from the command line."""
    parser = argparse.ArgumentParser(description="Ghidra Analyzer CLI")
    parser.add_argument("query", nargs="?", default=None, 
                        help="The query to execute (if not provided, will prompt)")
    parser.add_argument("--log-level", default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level")
    parser.add_argument("--example", type=int, choices=range(1, 5), 
                        help="Run an example query (1-4)")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Example queries
    examples = {
        1: "List all functions in the current program",
        2: "What does the main function do?",
        3: "Recursively traverse the functions from entry and describe the programmatic behavior",
        4: "Analyze the function at address 0x401000 and suggest a better name based on its behavior"
    }
    
    # Get the query
    query = None
    if args.example:
        query = examples[args.example]
        print(f"Running example query: {query}")
    elif args.query:
        query = args.query
    else:
        print("Enter your query for Ghidra analysis (Ctrl+D to submit):")
        query = sys.stdin.read().strip()
    
    if not query:
        print("No query provided. Exiting.")
        return 1
    
    # Create the Ghidra analyzer pipeline
    try:
        print(f"Initializing Ghidra analyzer...")
        analyzer = build_ghidra_analyzer_pipeline()
        
        print(f"Executing query: {query}")
        result = analyzer.execute({"user_query": query})
        
        print("\n=== ANALYSIS RESULT ===\n")
        analysis = result.get("current_analysis", "No analysis generated")
        print(analysis)
        print("\n=======================\n")
        return 0
    
    except Exception as e:
        logging.error(f"Error executing Ghidra analyzer: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 