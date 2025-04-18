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
        if self.config.summarization_model:
            logger.info(f"Using specialized model for summarization: {config.summarization_model}")
        
        # Log any phase-specific models that are configured
        for phase, model in self.config.model_map.items():
            if model:
                logger.info(f"Using specialized model for {phase} phase: {model}")
    
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
        return self._generate_with_model(self.config.model, prompt, system_prompt)
    
    def generate_for_phase(self, phase: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to a phase-specific Ollama model and get a response.
        If no model is specified for the phase, uses the default model.
        
        Args:
            phase: The phase of processing (planning, execution, review, etc.)
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            The model's response as a string
            
        Raises:
            Exception: If the request fails
        """
        # Determine which model to use for this phase
        model = self.config.model  # Default model
        
        # Check if we have a specific model for this phase
        if phase in self.config.model_map and self.config.model_map[phase]:
            model = self.config.model_map[phase]
            logger.info(f"Using phase-specific model for {phase}: {model}")
        
        # Check if we have a specific system prompt for this phase
        if system_prompt is None and phase in self.config.phase_system_prompts and self.config.phase_system_prompts[phase]:
            system_prompt = self.config.phase_system_prompts[phase]
            logger.info(f"Using phase-specific system prompt for {phase}")
        
        # Special case for summarization
        if phase == "summarization" and not self.config.model_map.get("summarization") and self.config.summarization_model:
            model = self.config.summarization_model
            logger.info(f"Using summarization model for summarization phase: {model}")
            if system_prompt is None:
                system_prompt = self.config.summarization_system_prompt
                logger.info("Using summarization system prompt")
        
        return self._generate_with_model(model, prompt, system_prompt)
        
    def generate_with_summarization_model(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to the summarization model and get a response.
        If no summarization model is configured, falls back to the main model.
        
        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            The model's response as a string
            
        Raises:
            Exception: If the request fails
        """
        model = self.config.summarization_model if self.config.summarization_model else self.config.model
        if system_prompt is None and self.config.summarization_model:
            system_prompt = self.config.summarization_system_prompt
            
        logger.info(f"Using {'specialized summarization' if model != self.config.model else 'default'} model: {model}")
        return self._generate_with_model(model, prompt, system_prompt)
    
    def _generate_with_model(self, model: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Internal method to send a prompt to a specific Ollama model and get a response.
        
        Args:
            model: The specific model to use
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            The model's response as a string
            
        Raises:
            Exception: If the request fails
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False  # Explicitly disable streaming to get a single JSON response
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.debug(f"Sending prompt to Ollama model '{model}': {prompt[:100]}...")
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