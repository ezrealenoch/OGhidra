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

try:
    logger.debug("Attempting to import ghidra_analyzer agent")
    # Import the globally defined agent instance directly
    from src.adk_agents.ghidra_analyzer.agents import agent 
    # The imported agent is already the instance we need.
    logger.debug(f"Successfully imported agent instance: {agent}")
except Exception as e:
    logger.error(f"Error importing ghidra_analyzer agent: {e}", exc_info=True)
    # Create a dummy agent to prevent crashing when module is imported
    from google.adk.agents import LlmAgent, LoopAgent
    from google.adk.models.lite_llm import LiteLlm

    class DummyAgent(LlmAgent):
        def __init__(self):
            super().__init__(
                name="DummyAgent", 
                model=LiteLlm(model="ollama/mistral"),
                instruction="This is a dummy agent due to an import error."
            )
    
    agent = DummyAgent()
    logger.warning(f"Using dummy agent due to import error: {agent}") 