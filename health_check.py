#!/usr/bin/env python3
"""
Health check script for Ollama and GhidraMCP services.
"""

import os
import sys
import httpx
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("health-check")

# Get configuration from environment or use defaults
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "cogito:32b")
GHIDRA_MCP_URL = os.getenv("GHIDRA_MCP_URL", "http://localhost:8080")

def check_ollama():
    """Check if Ollama service is running and the model is available."""
    logger.info(f"Checking Ollama at {OLLAMA_API_BASE}...")
    
    try:
        # Basic connectivity check
        response = httpx.get(OLLAMA_API_BASE, timeout=5)
        if response.status_code != 200:
            logger.error(f"Ollama server returned status code {response.status_code}")
            return False
        
        # Check if the model is available
        models_url = f"{OLLAMA_API_BASE}/api/tags"
        response = httpx.get(models_url, timeout=5)
        if response.status_code != 200:
            logger.error(f"Failed to list Ollama models, status code {response.status_code}")
            return False
        
        # Parse model list
        models_data = response.json()
        available_models = [model.get("name") for model in models_data.get("models", [])]
        
        # Extract just the model name without provider prefix
        model_name = OLLAMA_MODEL
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        
        if model_name not in available_models:
            logger.error(f"Model '{model_name}' not found in available models: {available_models}")
            logger.info(f"Please run: ollama pull {model_name}")
            return False
            
        logger.info(f"Ollama is running and model '{model_name}' is available.")
        return True
        
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        return False

def check_ghidra():
    """Check if GhidraMCP service is running."""
    logger.info(f"Checking GhidraMCP at {GHIDRA_MCP_URL}...")
    
    try:
        # Test these endpoints in order - these are known to exist in GhidraMCP
        endpoints = [
            "/list_functions",
            "/list_methods",
            "/get_current_function",
            "/get_current_address"
        ]
        
        for endpoint in endpoints:
            try:
                response = httpx.get(f"{GHIDRA_MCP_URL}{endpoint}", timeout=5)
                if response.status_code == 200:
                    logger.info(f"GhidraMCP is running and responding to {endpoint}")
                    
                    # Check if we have actual data or just test data
                    content = response.text.strip()
                    if content:
                        if endpoint == "/list_functions" or endpoint == "/list_methods":
                            lines = content.split('\n')
                            if len(lines) > 0:
                                sample = lines[:3]
                                logger.info(f"Found {len(lines)} items. Sample: {sample}")
                                
                                # Check for mock data patterns
                                mock_patterns = ["malware.exe", "hello world", "test_func"]
                                if any(any(pattern in line.lower() for pattern in mock_patterns) for line in sample):
                                    logger.warning("Note: Response appears to contain test/mock data")
                    
                    return True
            except httpx.RequestError as e:
                logger.warning(f"Failed to connect to {endpoint}: {e}")
                continue
        
        # Try alternate formats (some GhidraMCP versions use different endpoint naming)
        alt_endpoints = [
            "/methods",
            "/functions",
            "/current_function"
        ]
        
        for endpoint in alt_endpoints:
            try:
                response = httpx.get(f"{GHIDRA_MCP_URL}{endpoint}", timeout=5)
                if response.status_code == 200:
                    logger.info(f"GhidraMCP is running and responding to alternate endpoint {endpoint}")
                    return True
            except httpx.RequestError:
                continue
        
        logger.error(f"GhidraMCP server at {GHIDRA_MCP_URL} is not responding to any known endpoints.")
        logger.info("Make sure that the GhidraMCP plugin is enabled and the server has been started.")
        return False
        
    except Exception as e:
        logger.error(f"Error connecting to GhidraMCP: {e}")
        return False

def main():
    """Run all health checks."""
    logger.info("Starting health checks...")
    
    # Check Ollama
    ollama_ok = check_ollama()
    
    # Check GhidraMCP
    ghidra_ok = check_ghidra()
    
    # Summary
    logger.info("\n===== Health Check Summary =====")
    logger.info(f"Ollama: {'OK' if ollama_ok else 'FAILED'}")
    logger.info(f"GhidraMCP: {'OK' if ghidra_ok else 'FAILED'}")
    
    if not ollama_ok:
        logger.info("\nOllama Troubleshooting:")
        logger.info("1. Make sure Ollama is running: 'ollama serve'")
        logger.info(f"2. Verify your API URL: {OLLAMA_API_BASE}")
        logger.info(f"3. Check if model is available: 'ollama list' (or pull it: 'ollama pull {OLLAMA_MODEL}')")
    
    if not ghidra_ok:
        logger.info("\nGhidraMCP Troubleshooting:")
        logger.info("1. Make sure Ghidra is running and GhidraMCP plugin is installed")
        logger.info("2. Verify GhidraMCP server is running")
        logger.info(f"3. Check server URL: {GHIDRA_MCP_URL}")
        logger.info("4. In Ghidra, check: Edit -> Tool Options -> GhidraMCP HTTP Server")
    
    return 0 if ollama_ok and ghidra_ok else 1

if __name__ == "__main__":
    sys.exit(main()) 