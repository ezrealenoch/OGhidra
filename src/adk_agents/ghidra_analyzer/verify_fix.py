#!/usr/bin/env python3
"""
Verification script for testing the fixed ADK agent Ghidra connectivity.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import time
import asyncio

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify-fix")

# Import Ghidra functions from ADK tools
try:
    from src.adk_tools.ghidra_mcp import (
        verify_ghidra_mcp_connection,
        ghidra_list_functions,
        ghidra_get_current_program
    )
    from google.adk.models.lite_llm import LiteLlm
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Please make sure you're running from the project root directory")
    sys.exit(1)

async def test_litellm_connection():
    """Test if LiteLLM can connect to Ollama."""
    logger.info("Testing LiteLLM connection to Ollama...")
    
    # Configure LiteLLM to use Ollama
    OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", "cogito:32b")
    if not OLLAMA_MODEL_NAME.startswith("ollama/"):
        OLLAMA_MODEL_STRING = f"ollama/{OLLAMA_MODEL_NAME}"
    else:
        OLLAMA_MODEL_STRING = OLLAMA_MODEL_NAME
    
    if not os.getenv("OLLAMA_API_BASE"):
        os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"
    
    try:
        logger.info(f"Initializing LiteLlm with model: {OLLAMA_MODEL_STRING}")
        llm = LiteLlm(model=OLLAMA_MODEL_STRING)
        
        # Test with a simple request
        content = [{"text": "Say hello in one word"}]
        
        logger.info("Sending test request to LiteLLM...")
        response = await llm.generate_content_async(content)
        
        if not response or response.text is None:
            logger.error("LiteLLM response was empty")
            return False
        
        logger.info(f"LiteLLM response: {response.text}")
        return True
    except Exception as e:
        logger.error(f"Error testing LiteLLM connection: {e}")
        return False

def test_ghidra_connection():
    """Test if we can connect to the GhidraMCP server."""
    logger.info("Testing GhidraMCP connection...")
    
    # Check connection
    conn_status = verify_ghidra_mcp_connection()
    if conn_status["status"] != "success":
        logger.error(f"GhidraMCP connection failed: {conn_status['message']}")
        return False
    
    # Try to get functions
    logger.info("Getting function list from GhidraMCP...")
    functions = ghidra_list_functions()
    if functions["status"] != "success":
        logger.error(f"Failed to get functions: {functions['message']}")
        return False
    
    # Display functions
    logger.info(f"Found {len(functions['result'])} functions in current program")
    if functions['result']:
        logger.info(f"Sample functions: {functions['result'][:5]}")
    
    # Try to get current program
    program = ghidra_get_current_program()
    if program["status"] == "success":
        logger.info(f"Current program: {program['result']}")
    else:
        logger.warning(f"Could not get current program: {program['message']}")
    
    return True

async def main():
    """Run verification tests."""
    logger.info("Starting verification of fixes...")
    
    # Test GhidraMCP connection
    ghidra_ok = test_ghidra_connection()
    
    # Test LiteLLM/Ollama connection
    ollama_ok = await test_litellm_connection()
    
    # Summary
    logger.info("\n===== Verification Results =====")
    logger.info(f"GhidraMCP connection: {'OK' if ghidra_ok else 'FAILED'}")
    logger.info(f"LiteLLM/Ollama connection: {'OK' if ollama_ok else 'FAILED'}")
    
    if ghidra_ok and ollama_ok:
        logger.info("\nAll connections are working properly! The fix is successful.")
        return 0
    else:
        logger.error("\nSome connections are still failing. Further debugging required.")
        return 1

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        logger.info("Verification interrupted by user")
        sys.exit(1) 