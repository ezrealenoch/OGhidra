"""
Configuration module for the Ollama-GhidraMCP Bridge.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class OllamaConfig:
    """Configuration for the Ollama client."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    summarization_model: str = ""  # Empty string means use the main model
    timeout: int = 120  # Timeout for requests in seconds
    
    # System prompt for guiding the AI's responses
    default_system_prompt: str = """
    You are an AI assistant specialized in reverse engineering with Ghidra.
    You can help analyze binary files by executing commands through GhidraMCP.
    
    Available commands:
    - list_methods(offset, limit): List all function names with pagination
    - list_classes(offset, limit): List all namespace/class names with pagination
    - decompile_function(name): Decompile a specific function by name
    - rename_function(old_name, new_name): Rename a function
    - rename_data(address, new_name): Rename a data label at an address
    - list_segments(offset, limit): List memory segments with pagination
    - list_imports(offset, limit): List imported symbols with pagination
    - list_exports(offset, limit): List exported symbols with pagination
    - list_namespaces(offset, limit): List all non-global namespaces with pagination
    - list_data_items(offset, limit): List defined data labels with pagination
    - search_functions_by_name(query, offset, limit): Search functions by name
    - rename_variable(function_name, old_name, new_name): Rename a local variable
    - get_function_by_address(address): Get function by address
    - get_current_address(): Get currently selected address
    - get_current_function(): Get currently selected function
    - list_functions(): List all functions in the database
    - decompile_function_by_address(address): Decompile function at address
    - disassemble_function(address): Get assembly code for a function
    - set_decompiler_comment(address, comment): Set a comment in pseudocode
    - set_disassembly_comment(address, comment): Set a comment in disassembly
    - rename_function_by_address(function_address, new_name): Rename function by address
    - set_function_prototype(function_address, prototype): Set a function's prototype
    - set_local_variable_type(function_address, variable_name, new_type): Set variable type
    
    When responding, if you need to perform an action in Ghidra, use the format:
    EXECUTE: command_name(param1="value1", param2="value2")
    
    For example:
    EXECUTE: decompile_function(name="main")
    EXECUTE: list_functions()
    EXECUTE: disassemble_function(address="0x1000")
    """
    
    # System prompt specifically for summarization tasks
    summarization_system_prompt: str = """
    You are a specialized AI assistant for summarizing and organizing technical information about reverse engineering and binary analysis. 
    Your task is to create a comprehensive, well-structured report based on the information provided.
    
    Focus on:
    1. Extracting key insights and findings
    2. Organizing information logically
    3. Highlighting important technical details about functions, memory, and program behavior
    4. Summarizing the overall purpose and behavior of the analyzed binary
    5. Providing clear conclusions
    
    Format your response as a structured report with clearly delineated sections using Markdown.
    """

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
        return cls(
            ollama=OllamaConfig(
                base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
                model=os.environ.get("OLLAMA_MODEL", "llama3"),
                summarization_model=os.environ.get("OLLAMA_SUMMARIZATION_MODEL", ""),  # Default to empty (use main model)
                timeout=int(os.environ.get("OLLAMA_TIMEOUT", "120")),
            ),
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