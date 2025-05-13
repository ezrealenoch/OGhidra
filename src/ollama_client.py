#!/usr/bin/env python3
"""
Ollama Client for OGhidra
-------------------------
Handles communication with the Ollama API for AI model interactions.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, config):
        """
        Initialize the Ollama client.
        
        Args:
            config: OllamaConfig object or similar with attributes:
                - base_url: Base URL for Ollama API
                - model: Default model to use
                - system_prompt: Default system prompt
                - temperature: Temperature for generation
                - max_tokens: Maximum tokens to generate
        """
        self.base_url = getattr(config, 'base_url', 'http://localhost:11434')
        self.default_model = getattr(config, 'model', 'llama2')
        self.default_system_prompt = getattr(config, 'system_prompt', '')
        self.temperature = getattr(config, 'temperature', 0.7)
        self.max_tokens = getattr(config, 'max_tokens', 2000)
        self.logger = logging.getLogger("ollama-client")
        self.model_map = getattr(config, 'model_map', {})
        
    def generate(self, 
                prompt: str, 
                model: Optional[str] = None,
                system_prompt: Optional[str] = None,
                temperature: Optional[float] = None,
                max_tokens: Optional[int] = None) -> str:
        """
        Generate a response from the Ollama model.
        
        Args:
            prompt: The input prompt
            model: Optional model override
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            Generated response text
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": model or self.default_model,
            "prompt": prompt,
            "system": system_prompt or self.default_system_prompt,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False  # Disable streaming to get a single response
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get('response', '')
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error calling Ollama API: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing Ollama API response: {str(e)}")
            raise
            
    def generate_with_phase(self,
                          prompt: str,
                          phase: Optional[str] = None,
                          system_prompt: Optional[str] = None) -> str:
        """
        Generate a response using a phase-specific model if configured.
        
        Args:
            prompt: The input prompt
            phase: Optional phase name ('planning', 'execution', 'analysis')
            system_prompt: Optional system prompt override
            
        Returns:
            Generated response text
        """
        # Get the model for this phase if configured
        model = self.model_map.get(phase) if phase else None
        
        # Generate the response using the phase-specific model or default
        return self.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt
        )
            
    def list_models(self) -> List[str]:
        """
        List available models from Ollama.
        
        Returns:
            List of model names
        """
        url = f"{self.base_url}/api/tags"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return [model['name'] for model in response.json()['models']]
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error listing Ollama models: {str(e)}")
            raise

    def check_health(self) -> bool:
        """
        Check if the Ollama server is reachable and healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False
