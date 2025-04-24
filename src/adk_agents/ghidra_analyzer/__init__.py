"""
Exposes the Ghidra Analyzer loop agent for discovery by ADK.
"""

# Import the main LoopAgent instance from the agents module
from .agents import agent

# The variable name 'agent' is conventionally used by ADK for discovery.
__all__ = ['agent'] 