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
    # Default model. This is primarily set by the OLLAMA_MODEL environment variable.
    # llama3.1 is recommended for features like tool calling.
    model: str = "gemma3:27b"
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
    You are a Planning Assistant for Ghidra reverse engineering tasks.
    Your task is to create a plan using the available Ghidra tools.

    AVAILABLE TOOLS:
    - list_methods(offset, limit): List function names
    - list_classes(offset, limit): List namespace/class names
    - decompile_function(name): Decompile function by name
    - rename_function(old_name, new_name): Rename function by name
    - rename_function_by_address(function_address, new_name): Rename function by address
    - list_functions(): List all functions
    - decompile_function_by_address(address): Decompile function by address
    - list_imports(offset, limit): List imported symbols
    - list_exports(offset, limit): List exported symbols
    - list_segments(offset, limit): List memory segments
    - search_functions_by_name(query, offset, limit): Search functions by name

    OUTPUT FORMAT:
    PLAN:
    TOOL: <tool_name> PARAMS: <param1>="<value1>", <param2>=<value2>

    RULES:
    1. Start with "PLAN:"
    2. Each line must start with "TOOL: "
    3. Use exact tool names from the list above
    4. String values must be in double quotes
    5. Numerical values should not be quoted
    6. If no parameters, use " PARAMS: " with nothing after

    EXAMPLES:
    PLAN:
    TOOL: decompile_function PARAMS: name="main"
    TOOL: list_imports PARAMS: offset=0, limit=50
    TOOL: list_functions PARAMS: 

    IMPORTANT: Only create the plan, do not execute or analyze.
    """
    
    execution_system_prompt: str = """
    You are a Tool Execution Assistant for Ghidra reverse engineering tasks.
    Your task is to help the user achieve their goal by executing Ghidra tool calls.

    Review the conversation context and determine the next best tool to call to progress toward the stated goal.
    If you believe the goal has been achieved or no more tool calls are needed, say "GOAL ACHIEVED".

    AVAILABLE TOOLS (EXACT SYNTAX - DO NOT MODIFY):
    - list_functions(): List all functions (no parameters required)
    - list_methods(offset=0, limit=100): List function names with pagination
    - list_classes(offset=0, limit=100): List namespace/class names with pagination
    - decompile_function(name="FunctionName"): Decompile a function BY NAME
    - rename_function(old_name="OldName", new_name="NewName"): Rename function by name
    - rename_function_by_address(address="1400011a8", new_name="NewName"): Rename function by address
    - decompile_function_by_address(address="1400011a8"): Decompile function BY ADDRESS
    - list_imports(offset=0, limit=50): List imported symbols
    - list_exports(offset=0, limit=50): List exported symbols
    - list_segments(offset=0, limit=20): List memory segments
    - search_functions_by_name(query="main", offset=0, limit=20): Search functions by name

    REQUIRED FORMAT:
    EXECUTE: exact_tool_name(param1="value1", param2="value2")

    CORRECT EXAMPLES:
    EXECUTE: list_functions()
    EXECUTE: decompile_function(name="main")
    EXECUTE: decompile_function_by_address(address="1400011a8")
    EXECUTE: search_functions_by_name(query="init", limit=20)

    INCORRECT EXAMPLES (WILL FAIL):
    EXECUTE: decompile()  ❌ (missing required parameters)
    EXECUTE: disassemble(address="1400011a8")  ❌ (not a valid command)
    EXECUTE: decompile_function()  ❌ (missing required parameter 'name')

    IMPORTANT:
    1. Use EXACT command names from the list above
    2. ALWAYS include ALL required parameters
    3. Put string values in double quotes
    4. Do not put quotes around numeric values
    5. For address-based tools, provide the address as a string (e.g., "140001000")
    """
    
    # Best practices for function calls
    FUNCTION_CALL_BEST_PRACTICES = """
    # COMMON ERRORS TO AVOID:
    # ✓ DO use snake_case for function names: decompile_function not decompileFunction
    # ✓ DO NOT use the "FUN_" prefix in addresses: address="14024DA90" not address="FUN_14024DA90"
    # ✓ DO NOT use "0x" prefix in addresses: address="14024DA90" not address="0x14024DA90"
    # ✓ DO check that a function exists before trying to decompile or rename it
    # ✓ DO use the list_functions() tool to find available functions 
    # ✓ DO use name="FUN_14024DA90" for decompile_function, NOT address="14024DA90"
    # ✓ DO use address="14024DA90" for decompile_function_by_address, NOT name="FUN_14024DA90"
    """
    
    evaluation_system_prompt: str = """
    You are a Goal Evaluation Assistant for Ghidra reverse engineering tasks.
    Your task is to determine if the stated goal has been achieved based on the tools executed and their results.

    Consider:
    1. What was the original goal?
    2. Have all necessary tools been executed successfully?
    3. Is there enough information to provide a complete answer?
    4. Are there any critical errors that prevent goal completion?

    If the goal has been achieved, respond with "GOAL ACHIEVED".
    If more tool calls are needed, respond with "GOAL NOT ACHIEVED" and briefly explain what's missing.
    """
    
    analysis_system_prompt: str = """
    You are an analysis assistant specialized in reverse engineering with Ghidra.
    Your task is to analyze the results of the tool executions and provide a comprehensive
    answer to the user's query. Focus on clear explanations and actionable insights.
    
    When presenting results:
    1. For function listings, show at least some sample entries, not just totals
    2. For decompiled code, include the relevant portions with explanations
    3. Always include specific details from the tool results, not just summaries
    4. Format your output for readability using proper spacing, headers, and bullet points
    
    Prefix your final answer with "FINAL RESPONSE:" to mark the conclusion of your analysis.
    """
    
    # System prompts for different phases
    phase_system_prompts: Dict[str, str] = field(default_factory=lambda: {
        "planning": "",    # If empty, use planning_system_prompt
        "execution": "",   # If empty, use execution_system_prompt
        "analysis": "",    # If empty, use analysis_system_prompt
        "evaluation": "",  # If empty, use evaluation_system_prompt
        "review": ""       # If empty, use analysis_system_prompt for review
    })

@dataclass
class GhidraMCPConfig:
    """Configuration for the GhidraMCP client."""
    base_url: str = "http://localhost:8080"
    timeout: int = 30  # Timeout for requests in seconds
    mock_mode: bool = False  # Enable mock mode for testing without a GhidraMCP server
    api_path: str = ""  # Optional API path for GhidraMCP
    extended_url: str = "http://localhost:8081"  # Added extended_url field

@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    log_file: str = "bridge.log"
    console_logging: bool = True
    file_logging: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

@dataclass
class SessionHistoryConfig:
    """Configuration for session history."""
    enabled: bool = True
    storage_path: str = "data/ollama_ghidra_session_history.jsonl"
    # Maximum number of sessions to keep in history
    max_sessions: int = 1000
    # Whether to generate summaries automatically at the end of sessions
    auto_summarize: bool = True
    # Whether to use vector embeddings for RAG
    use_vector_embeddings: bool = False
    # Path to the vector database
    vector_db_path: str = "data/vector_db"

@dataclass
class BridgeConfig:
    """Configuration for the Bridge."""
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    ghidra: GhidraMCPConfig = field(default_factory=GhidraMCPConfig)
    session_history: SessionHistoryConfig = field(default_factory=SessionHistoryConfig)
    log_level: str = "INFO"
    log_file: str = "bridge.log"
    log_console: bool = True
    log_file_enabled: bool = True
    context_limit: int = 5  # Number of previous exchanges to include in context
    max_steps: int = 5  # Maximum number of steps for tool execution
    
    # CAG Configuration
    cag_enabled: bool = True
    cag_knowledge_cache_enabled: bool = True
    cag_session_cache_enabled: bool = True
    cag_token_limit: int = 2000

    # Enable or disable Context-Augmented Generation
    ENABLE_CAG = True
    
    # Enable or disable Knowledge Base
    ENABLE_KNOWLEDGE_BASE = True
    
    # Knowledge Base directory
    KNOWLEDGE_BASE_DIR = "knowledge_base"
    
    # Maximum steps for each phase
    MAX_STEPS = 5
    MAX_GOAL_STEPS = 5
    MAX_REVIEW_STEPS = 5
    
    # Enable or disable review phase
    ENABLE_REVIEW = True

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """
        Create a BridgeConfig object from environment variables.

        Returns:
            BridgeConfig object
        """
        # Load Ollama configuration
        ollama_config = OllamaConfig(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
        )
        
        # Load phase-specific models if defined
        ollama_config.planning_model = os.getenv("OLLAMA_MODEL_PLANNING", ollama_config.model)
        ollama_config.execution_model = os.getenv("OLLAMA_MODEL_EXECUTION", ollama_config.model)
        ollama_config.analysis_model = os.getenv("OLLAMA_MODEL_ANALYSIS", ollama_config.model)
        
        # Load GhidraMCP configuration
        ghidra_config = GhidraMCPConfig(
            base_url=os.getenv("GHIDRA_MCP_URL", "http://localhost:8080"),
            timeout=int(os.getenv("GHIDRA_MCP_TIMEOUT", "30")),
            mock_mode=os.getenv("GHIDRA_MOCK_MODE", "false").lower() == "true",
            api_path=os.getenv("GHIDRA_API_PATH", ""),
            extended_url=os.getenv("GHIDRA_MCP_EXTENDED_URL", "http://localhost:8081"),
        )
        
        # Load session history configuration
        session_history_config = SessionHistoryConfig(
            enabled=os.getenv("SESSION_HISTORY_ENABLED", "true").lower() == "true",
            storage_path=os.getenv("SESSION_HISTORY_PATH", "data/ollama_ghidra_session_history.jsonl"),
            max_sessions=int(os.getenv("SESSION_HISTORY_MAX_SESSIONS", "1000")),
            auto_summarize=os.getenv("SESSION_HISTORY_AUTO_SUMMARIZE", "true").lower() == "true",
            use_vector_embeddings=os.getenv("SESSION_HISTORY_USE_VECTOR_EMBEDDINGS", "false").lower() == "true",
            vector_db_path=os.getenv("SESSION_HISTORY_VECTOR_DB_PATH", "data/vector_db"),
        )
        
        # Load logging configuration
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file = os.getenv("LOG_FILE", "bridge.log")
        log_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        log_file_enabled = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
        
        # Load Bridge configuration
        context_limit = int(os.getenv("CONTEXT_LIMIT", "5"))
        max_steps = int(os.getenv("MAX_STEPS", "5"))
        
        # Load CAG configuration
        cag_enabled = os.getenv("CAG_ENABLED", "true").lower() == "true"
        cag_knowledge_cache_enabled = os.getenv("CAG_KNOWLEDGE_CACHE_ENABLED", "true").lower() == "true"
        cag_session_cache_enabled = os.getenv("CAG_SESSION_CACHE_ENABLED", "true").lower() == "true"
        cag_token_limit = int(os.getenv("CAG_TOKEN_LIMIT", "2000"))
        
        return cls(
            ollama=ollama_config,
            ghidra=ghidra_config,
            session_history=session_history_config,
            log_level=log_level,
            log_file=log_file,
            log_console=log_console,
            log_file_enabled=log_file_enabled,
            context_limit=context_limit,
            max_steps=max_steps,
            cag_enabled=cag_enabled,
            cag_knowledge_cache_enabled=cag_knowledge_cache_enabled,
            cag_session_cache_enabled=cag_session_cache_enabled,
            cag_token_limit=cag_token_limit
        ) 