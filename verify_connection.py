#!/usr/bin/env python3
"""
Simple connection verification script that tests both the Ollama and GhidraMCP connections.
"""

import os
import sys
import logging
import httpx
import time
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify-connection")

# Get configuration from environment or use defaults
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "cogito:32b")
GHIDRA_MCP_URL = os.getenv("GHIDRA_MCP_URL", "http://localhost:8080")

async def test_litellm_connection():
    """Test connection to Ollama via LiteLLM."""
    logger.info(f"Testing LiteLLM connection to Ollama with model {OLLAMA_MODEL}...")
    
    try:
        # Try importing LiteLLM
        from litellm import completion
        
        # If using Ollama, ensure model has prefix
        model_name = OLLAMA_MODEL
        if not model_name.startswith("ollama/"):
            model_name = f"ollama/{model_name}"
        
        logger.info(f"Sending test completion to {model_name}...")
        response = await asyncio.to_thread(
            completion,
            model=model_name,
            messages=[{"role": "user", "content": "Say hello in one word"}],
            temperature=0.7,
            max_tokens=10,
        )
        
        logger.info(f"LiteLLM response: {response.choices[0].message.content}")
        return True
    except ImportError:
        logger.error("LiteLLM is not installed. Run: pip install litellm")
        return False
    except Exception as e:
        logger.error(f"Error testing LiteLLM connection: {e}")
        logger.info("Try running 'ollama serve' if Ollama is not already running")
        return False

def test_ghidra_mcp():
    """Test connection to GhidraMCP server."""
    logger.info(f"Testing connection to GhidraMCP at {GHIDRA_MCP_URL}...")
    
    try:
        # Try these endpoints in order
        primary_endpoints = [
            "list_functions",
            "list_methods", 
            "get_current_function"
        ]
        
        # Try alternate endpoint formats used by some GhidraMCP versions
        alternate_endpoints = [
            "methods",
            "functions",
            "current_function"
        ]
        
        # Try all primary endpoints
        for endpoint in primary_endpoints:
            try:
                with httpx.Client(timeout=5) as client:
                    logger.info(f"Trying endpoint: /{endpoint}")
                    response = client.get(f"{GHIDRA_MCP_URL}/{endpoint}")
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully connected to GhidraMCP via /{endpoint}")
                        
                        # Check content to identify actual vs mock data
                        content = response.text.strip()
                        if content and (endpoint == "list_functions" or endpoint == "list_methods"):
                            lines = content.split('\n')
                            if lines:
                                count = len(lines)
                                sample = lines[:min(3, count)]
                                logger.info(f"Found {count} items. Sample: {sample}")
                                
                                # Check for mock data patterns
                                mock_patterns = ["malware.exe", "hello world"]
                                if any(any(pattern in line.lower() for pattern in mock_patterns) for line in sample):
                                    logger.warning(f"⚠️ Response contains mock/test data. GhidraMCP may not be connected to a real binary.")
                        
                        return True
            except Exception as e:
                logger.warning(f"Failed to connect to /{endpoint}: {e}")
                continue
        
        # Try alternate endpoints
        for endpoint in alternate_endpoints:
            try:
                with httpx.Client(timeout=5) as client:
                    logger.info(f"Trying alternate endpoint: /{endpoint}")
                    response = client.get(f"{GHIDRA_MCP_URL}/{endpoint}")
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully connected to GhidraMCP via alternate endpoint /{endpoint}")
                        return True
            except Exception:
                continue
        
        logger.error(f"Could not connect to any GhidraMCP endpoint at {GHIDRA_MCP_URL}")
        logger.info("""
Troubleshooting tips:
1. Make sure Ghidra is running
2. Check that the GhidraMCP plugin is installed and enabled in Ghidra
3. In Ghidra, go to Edit -> Tool Options -> GhidraMCP HTTP Server to verify server settings
4. Ensure the server has been started (Window -> GhidraMCP Server -> Start Server)
5. Check that the port in your .env file (GHIDRA_MCP_URL) matches Ghidra's configuration
""")
        return False
    
    except Exception as e:
        logger.error(f"Error testing GhidraMCP connection: {e}")
        return False

async def main():
    """Run all verification tests."""
    logger.info("Starting connection verification...")
    
    # Test GhidraMCP connection
    ghidra_ok = test_ghidra_mcp()
    
    # Test Ollama/LiteLLM connection
    ollama_ok = await test_litellm_connection()
    
    # Summary
    logger.info("\n===== Connection Verification Results =====")
    logger.info(f"GhidraMCP: {'CONNECTED' if ghidra_ok else 'FAILED'}")
    logger.info(f"Ollama/LiteLLM: {'CONNECTED' if ollama_ok else 'FAILED'}")
    
    if ghidra_ok and ollama_ok:
        logger.info("\nAll connections verified! The ADK agent should work properly.")
        return 0
    else:
        logger.error("\nSome connections failed. See above for details.")
        return 1

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        logger.info("Verification interrupted by user")
        sys.exit(130) 