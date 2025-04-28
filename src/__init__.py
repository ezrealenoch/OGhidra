"""
Ollama-GhidraMCP Bridge
-----------------------
This package provides a bridge between Ollama and GhidraMCP for AI-assisted reverse engineering.
"""

__version__ = "0.1.0"

import logging
import os

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL", "").upper() == "DEBUG" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Import the main agent for ADK discovery.
# If this fails, the application should raise the ImportError.
logger.debug("Attempting to import ghidra_analyzer agent...")
from src.adk_agents.ghidra_analyzer.agents import root_agent as agent
logger.debug(f"Successfully imported agent instance: {agent}")

# The variable 'agent' is now directly assigned the imported root_agent. 