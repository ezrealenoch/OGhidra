"""
Ollama-GhidraMCP Bridge
-----------------------
This package provides a bridge between Ollama and GhidraMCP for AI-assisted reverse engineering.
"""

__version__ = "0.1.0"

# Explicitly import the agent object to make it discoverable under 'src'
try:
    from .adk_agents.ghidra_analyzer.agents import agent
except ImportError as e:
    # Handle case where the agent module might not exist or has issues
    print(f"Warning: Could not import agent from src.adk_agents.ghidra_analyzer: {e}")
    agent = None # Define agent as None if import fails 