"""
Configuration module for the Ollama-GhidraMCP Bridge.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class OllamaConfig:
    """Configuration for the Ollama client."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"  # Updated to llama3.1 which supports tool calling
    timeout: int = 120  # Timeout for requests in seconds
    
    # Model map for different phases of the simplified agentic loop
    # If a phase is not in the map or the value is empty, the default model will be used
    model_map: Dict[str, str] = field(default_factory=lambda: {
        "planning": "",       # Model for planning phase 
        "execution": "",      # Model for tool execution phase
        "analysis": ""        # Model for final analysis phase
    })
    
    # Simplified system prompt
    default_system_prompt: str = """
    You are an AI assistant specialized in reverse engineering with Ghidra.
    You can help analyze binary files by executing commands through GhidraMCP.
    """
    
    # Define tools for Ollama's tool calling API
    tools: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "type": "function",
            "function": {
                "name": "list_methods",
                "description": "List all function names with pagination",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "Offset to start from"},
                        "limit": {"type": "integer", "description": "Maximum number of results"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_classes",
                "description": "List all namespace/class names with pagination",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "Offset to start from"},
                        "limit": {"type": "integer", "description": "Maximum number of results"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "decompile_function",
                "description": "Decompile a specific function by name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Function name"}
                    },
                    "required": ["name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "rename_function",
                "description": "Rename a function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_name": {"type": "string", "description": "Current function name"},
                        "new_name": {"type": "string", "description": "New function name"}
                    },
                    "required": ["old_name", "new_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "rename_function_by_address",
                "description": "Rename function by address (IMPORTANT: Use numerical addresses only, not function names)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_address": {"type": "string", "description": "Function address (numerical only, like '1800011a8')"},
                        "new_name": {"type": "string", "description": "New function name"}
                    },
                    "required": ["function_address", "new_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_functions",
                "description": "List all functions in the database",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "decompile_function_by_address",
                "description": "Decompile function at address",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string", "description": "Function address"}
                    },
                    "required": ["address"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_imports",
                "description": "List imported symbols in the program",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "Offset to start from"},
                        "limit": {"type": "integer", "description": "Maximum number of results"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_exports", 
                "description": "List exported functions/symbols in the program",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "Offset to start from"},
                        "limit": {"type": "integer", "description": "Maximum number of results"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_segments",
                "description": "List all memory segments in the program",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "Offset to start from"},
                        "limit": {"type": "integer", "description": "Maximum number of results"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_functions_by_name",
                "description": "Search for functions by name substring",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "offset": {"type": "integer", "description": "Offset to start from"},
                        "limit": {"type": "integer", "description": "Maximum number of results"}
                    },
                    "required": ["query"]
                }
            }
        }
    ])
    
    # System prompt for each phase
    planning_system_prompt: str = """
    You are a planning assistant specialized in reverse engineering with Ghidra.
    Your task is to create a clear plan for analyzing binary files based on the user's request.
    Focus on understanding what the user is asking for and outlining the necessary steps.
    Do not execute any commands yet, just create a detailed plan.
    """
    
    execution_system_prompt: str = """
    You are a tool execution assistant specialized in reverse engineering with Ghidra.
    Your task is to execute the necessary Ghidra commands to fulfill the user's request.
    Use the EXECUTE: command_name(param1=value1, param2=value2) format to call commands.
    Focus on retrieving the information needed, not on analysis yet.
    """
    
    analysis_system_prompt: str = """
    You are an analysis assistant specialized in reverse engineering with Ghidra.
    Your task is to analyze the results of the tool executions and provide a comprehensive
    answer to the user's query. Focus on clear explanations and actionable insights.
    Prefix your final answer with "FINAL RESPONSE:" to mark the conclusion of your analysis.
    """
    
    # System prompts for different phases
    phase_system_prompts: Dict[str, str] = field(default_factory=lambda: {
        "planning": "",  # If empty, use planning_system_prompt
        "execution": "", # If empty, use execution_system_prompt
        "analysis": ""   # If empty, use analysis_system_prompt
    })

@dataclass
class GhidraMCPConfig:
    """Configuration for the GhidraMCP client."""
    base_url: str = "http://localhost:8080"
    timeout: int = 30  # Timeout for requests in seconds
    mock_mode: bool = False  # Enable mock mode for testing without a GhidraMCP server

@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    log_file: str = "bridge.log"
    console_logging: bool = True
    file_logging: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

@dataclass
class BridgeConfig:
    """Main configuration for the Bridge application."""
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    ghidra: GhidraMCPConfig = field(default_factory=GhidraMCPConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    context_limit: int = 5  # Number of previous exchanges to include in context
    
    @classmethod
    def from_env(cls) -> 'BridgeConfig':
        """Create a configuration from environment variables."""
        # Create base Ollama config with core settings
        ollama_config = OllamaConfig(
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
            timeout=int(os.environ.get("OLLAMA_TIMEOUT", "120")),
        )
        
        # Set up model map from environment variables
        model_map = {}
        for phase in ["planning", "execution", "analysis"]:
            env_var = f"OLLAMA_MODEL_{phase.upper()}"
            if env_var in os.environ:
                model_map[phase] = os.environ[env_var]
        
        # Only set if any values were defined
        if model_map:
            ollama_config.model_map = model_map
            
        # Set up system prompts for different phases from environment variables
        phase_prompts = {}
        for phase in ["planning", "execution", "analysis"]:
            env_var = f"OLLAMA_SYSTEM_PROMPT_{phase.upper()}"
            if env_var in os.environ:
                phase_prompts[phase] = os.environ[env_var]
                
        # Only set if any values were defined
        if phase_prompts:
            ollama_config.phase_system_prompts = phase_prompts
        
        return cls(
            ollama=ollama_config,
            ghidra=GhidraMCPConfig(
                base_url=os.environ.get("GHIDRA_MCP_URL", "http://localhost:8080"),
                timeout=int(os.environ.get("GHIDRA_MCP_TIMEOUT", "30")),
                mock_mode=os.environ.get("GHIDRA_MOCK_MODE", "false").lower() == "true",
            ),
            logging=LoggingConfig(
                level=os.environ.get("LOG_LEVEL", "INFO"),
                log_file=os.environ.get("LOG_FILE", "bridge.log"),
                console_logging=os.environ.get("LOG_CONSOLE", "true").lower() == "true",
                file_logging=os.environ.get("LOG_FILE_ENABLED", "true").lower() == "true",
            ),
            context_limit=int(os.environ.get("CONTEXT_LIMIT", "5")),
        ) 