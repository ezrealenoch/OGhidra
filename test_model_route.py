#!/usr/bin/env python3
"""
Test script for model routing with LiteLLM.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("model-route-test")

try:
    import litellm
    from litellm import completion
except ImportError:
    logger.error("LiteLLM not installed. Please run: pip install litellm")
    sys.exit(1)

# Define fallback models to try
MODELS_TO_TRY = [
    "ollama/phi3",
    "ollama/llama3",
    "gpt3.5-turbo", # Will fallback to OpenAI if configured
    "claude-3-haiku-20240307", # Will fallback to Anthropic if configured
]

def test_model(model_name):
    """Test connectivity to a specific model."""
    logger.info(f"Testing model: {model_name}")

    try:
        # If using Ollama, set the API base
        if model_name.startswith("ollama/"):
            os.environ["OLLAMA_API_BASE"] = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
            logger.info(f"Using Ollama API base: {os.environ['OLLAMA_API_BASE']}")

        # Simple completion request
        response = completion(
            model=model_name,
            messages=[{"role": "user", "content": "Say hello"}],
            temperature=0.7,
            max_tokens=100,
        )
        
        logger.info(f"Success! Response from {model_name}: {response.choices[0].message.content}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to {model_name}: {e}")
        return False

def main():
    """Try connecting to multiple models in sequence."""
    logger.info("Starting model route testing...")
    
    for model in MODELS_TO_TRY:
        if test_model(model):
            logger.info(f"Successfully connected to {model}. You can use this model in your .env file.")
            # Add more details about how to set up the environment
            if model.startswith("ollama/"):
                logger.info(f"To use this model, set: OLLAMA_MODEL={model}")
            else:
                logger.info(f"To use this model with LiteLLM, set the appropriate API keys and use: OLLAMA_MODEL={model}")
            return 0
    
    logger.error("Could not connect to any model. Please check your network and API configurations.")
    return 1

if __name__ == "__main__":
    sys.exit(main()) 