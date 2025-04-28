"""
Exposes the Ghidra Analyzer loop agent for discovery by ADK.
"""

# Import the main LoopAgent instance from the agents module
from .agents import root_agent

# The variable name 'root_agent' should be exported for ADK discovery.
__all__ = ['root_agent'] 