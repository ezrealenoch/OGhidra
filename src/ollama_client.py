"""
Client for interacting with the Ollama API.
"""

import json
import logging
from typing import Dict, Any, Optional, List

import httpx

from src.config import OllamaConfig

logger = logging.getLogger("ollama-ghidra-bridge.ollama")

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, config: OllamaConfig):
        """
        Initialize the Ollama client.
        
        Args:
            config: OllamaConfig object with connection details
        """
        self.config = config
        self.api_url = f"{config.base_url}/api/generate"
        self.client = httpx.Client(timeout=config.timeout)
        logger.info(f"Initialized Ollama client with model: {config.model}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to the Ollama model and get a response.
        
        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            The model's response as a string
            
        Raises:
            Exception: If the request fails
        """
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False  # Explicitly disable streaming to get a single JSON response
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.debug(f"Sending prompt to Ollama: {prompt[:100]}...")
            response = self.client.post(self.api_url, json=payload)
            response.raise_for_status()
            
            # Handle the response based on content
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    # Try to parse as a single JSON object
                    result = response.json()
                    logger.debug(f"Received response from Ollama: {result.get('response', '')[:100]}...")
                    return result.get("response", "")
                except json.JSONDecodeError:
                    # If it fails, try to parse as multiple JSON objects (stream)
                    response_text = response.text
                    # Handle case where we have multiple JSON objects (one per line)
                    lines = response_text.strip().split('\n')
                    if len(lines) > 1:
                        # Combine all responses in the stream
                        combined_response = ""
                        for line in lines:
                            try:
                                line_json = json.loads(line)
                                combined_response += line_json.get("response", "")
                            except json.JSONDecodeError as e:
                                logger.warning(f"Could not parse JSON line: {line}, error: {str(e)}")
                        return combined_response
                    else:
                        # If we can't handle it, just return the raw text
                        logger.warning("Could not parse JSON response, returning raw text")
                        return response_text
            else:
                # If not JSON, just return the text
                logger.warning(f"Received non-JSON response with content-type: {content_type}")
                return response.text
        except Exception as e:
            logger.error(f"Error communicating with Ollama: {str(e)}")
            raise
    
    def list_models(self) -> List[str]:
        """
        List available models on the Ollama server.
        
        Returns:
            List of model names
            
        Raises:
            Exception: If the request fails
        """
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            response.raise_for_status()
            result = response.json()
            models = [model.get("name") for model in result.get("models", [])]
            logger.info(f"Retrieved {len(models)} available models from Ollama")
            return models
        except Exception as e:
            logger.error(f"Error listing Ollama models: {str(e)}")
            raise

    def health_check(self) -> bool:
        """
        Check if the Ollama server is available.
        
        Returns:
            True if the server is available, False otherwise
        """
        try:
            response = self.client.get(f"{self.config.base_url}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama server health check failed: {str(e)}")
            return False 