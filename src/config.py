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
                        "address": {"type": "string", "description": "Function address (numerical only, like '1800011a8')"},
                        "new_name": {"type": "string", "description": "New function name"}
                    },
                    "required": ["address", "new_name"]
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
                "name": "analyze_function",
                "description": "Analyze a function including its code and all functions it calls",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string", "description": "Function address (optional)"}
                    }
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
    Your task is to create a plan using the available Ghidra tools. Carefully consider the user's query and select the most appropriate tools to achieve their goal.

    AVAILABLE TOOLS (Use these exact names and parameter conventions):
    - list_functions(): Lists all functions in the current program.
    - list_methods(offset, limit): List function names with pagination. (Consider using list_functions for a complete list if pagination is not desired).
    - list_classes(offset, limit): List namespace/class names with pagination.
    - decompile_function(name): Decompile function by its specific name (e.g., "FUN_14001000", "main").
    - decompile_function_by_address(address): Decompile function by its numerical address (e.g., "14001000").
    - rename_function(old_name, new_name): Rename function by its current name.
    - rename_function_by_address(address, new_name): Rename function by its numerical address.
    - list_imports(offset, limit): List imported symbols, showing external dependencies.
    - list_exports(offset, limit): List exported symbols, showing the program's public interface.
    - list_segments(offset, limit): List memory segments, providing information about memory layout.
    - search_functions_by_name(query, offset, limit): Search for functions by a name substring.
    - get_current_function(): Gets the function (name and address) at the current cursor position in Ghidra.
    - get_current_address(): Gets the address at the current cursor position in Ghidra.
    - analyze_function(address): Comprehensively analyze a function, including its code and all functions it calls. If no address is provided, analyzes the current function.

    OUTPUT FORMAT:
    PLAN:
    TOOL: <tool_name> PARAMS: <param1>="<value1>", <param2>=<value2>

    RULES:
    1. Start with "PLAN:"
    2. Each tool call must be on a new line starting with "TOOL: "
    3. Use exact tool names and parameter names as listed above.
    4. String values for parameters must be enclosed in double quotes.
    5. Numerical values for parameters should not be quoted.
    6. If a tool takes no parameters (e.g., list_functions), use " PARAMS: " with nothing after it.

    EXAMPLES:
    PLAN:
    TOOL: list_functions PARAMS: 
    TOOL: decompile_function PARAMS: name="main"
    TOOL: decompile_function_by_address PARAMS: address="14001050"
    TOOL: list_imports PARAMS: offset=0, limit=50
    TOOL: search_functions_by_name PARAMS: query="init", offset=0, limit=10
    TOOL: analyze_function PARAMS: address="14001050"

    IMPORTANT: Only create the plan. Do not generate explanatory text before "PLAN:" or after the tool calls. Focus solely on constructing the tool execution sequence.
    If the user asks for something not directly supported by a tool (e.g., "find all calls to function X" or "list all strings"), plan steps that would help gather relevant information (e.g., decompile related functions, search for function names that might handle strings). Do NOT invent tools.
    """
    
    execution_system_prompt: str = """
    You are a Tool Execution Assistant for Ghidra reverse engineering tasks.
    Your SOLE task is to help the user achieve their goal by selecting and proposing the execution of EXACTLY ONE Ghidra tool from the list below.

    Review the conversation context and the user's stated goal. Determine the single best tool call to make next.
    If you believe the goal has been met or no suitable tool exists in the list for the next logical step, output ONLY with the exact phrase "GOAL ACHIEVED".
    Otherwise, you MUST propose a tool call using the REQUIRED FORMAT.

    AVAILABLE TOOLS (Use EXACT syntax as shown - DO NOT MODIFY tool names or parameter names. Only these tools are available):
    - list_functions()
    - list_methods(offset=0, limit=100)
    - list_classes(offset=0, limit=100)
    - decompile_function(name="FunctionName")
    - decompile_function_by_address(address="1400011a8")
    - rename_function(old_name="OldName", new_name="NewName")
    - rename_function_by_address(address="1400011a8", new_name="NewName")
    - list_imports(offset=0, limit=50)
    - list_exports(offset=0, limit=50)
    - list_segments(offset=0, limit=20)
    - search_functions_by_name(query="main", offset=0, limit=20)
    - get_current_function()
    - get_current_address()
    - analyze_function(address="1400011a8")
    - analyze_function()  # Uses current function if no address provided

    HIGHLY RECOMMENDED FIRST TOOL FOR FUNCTION ANALYSIS:
    - analyze_function() - This will perform comprehensive analysis of the current function and all functions it calls.
      If analyzing a specific function, use analyze_function(address="1400011a8")
      THIS IS THE BEST CHOICE FOR REQUESTS LIKE: "analyze this function", "tell me what this function does", 
      "explain the function's behavior", "find malicious behavior", etc.

    REQUIRED FORMAT FOR TOOL EXECUTION (You MUST use this format):
    EXECUTE: exact_tool_name(param1="value1", param2="value2")

    STEPS:
    1. Analyze the current goal and existing information.
    2. If the goal is met or no suitable tool exists in the list for the next logical step, output "GOAL ACHIEVED".
    3. Otherwise, select the *most appropriate single tool* from the AVAILABLE TOOLS list to make progress.
    4. Construct the tool call precisely as specified in REQUIRED FORMAT FOR TOOL EXECUTION.
    5. Output *only* the EXECUTE line.

    CORRECT EXAMPLES OF YOUR RESPONSE:
    EXECUTE: list_imports(offset=0, limit=50)
    EXECUTE: decompile_function(name="main")
    EXECUTE: analyze_function()

    INCORRECT EXAMPLES (DO NOT DO THIS):
    EXECUTE: symbol_tree_imports()  ❌ (Tool not in AVAILABLE TOOLS list)
    Let's try listing imports: EXECUTE: list_imports() ❌ (Contains extra text, only EXECUTE line is allowed)
    No tool seems right. ❌ (If no tool, output "GOAL ACHIEVED")

    IMPORTANT RULES TO FOLLOW:
    1. ONLY use tool names and parameter names EXACTLY as they appear in the AVAILABLE TOOLS list.
    2. If a tool is not in the list, you CANNOT use it. Do not invent or assume tools (e.g., for Xrefs or string listing, as they are not in the list).
    3. ALWAYS include ALL required parameters for the chosen tool.
    4. String values for parameters MUST be in double quotes.
    5. Numerical values for parameters (e.g., offset, limit) should NOT be in quotes.
    6. For address-based tools, provide the address as a string (e.g., "140001000").
    7. If the user's query cannot be directly addressed by any single operation from the AVAILABLE TOOLS list (e.g., "find all callers of function X", "list all strings in the binary"), and you have executed all relevant preliminary tools (like listing imports/exports/functions), respond with "GOAL ACHIEVED" to indicate you cannot proceed further with the current toolset for that specific complex request.
    8. Output ONLY the EXECUTE line or "GOAL ACHIEVED". No other text, explanation, or conversational filler.
    9. When the user requests general function analysis or wants to understand what a function does, use analyze_function() (with or without an address as appropriate).
    """
    
    # Best practices for function calls
    FUNCTION_CALL_BEST_PRACTICES = """
    # COMMON ERRORS TO AVOID:
    # ✓ DO use snake_case for function names and parameter names (e.g., decompile_function, old_name).
    # ✓ Parameter 'address' for tools like decompile_function_by_address and rename_function_by_address refers to the numerical memory address.
    # ✓ DO NOT use the "FUN_" prefix when providing an address to tools expecting a numerical address (e.g., use address="14024DA90", not address="FUN_14024DA90").
    # ✓ DO NOT use "0x" prefix when providing an address (e.g., use address="14024DA90", not address="0x14024DA90").
    # ✓ DO ensure a function exists (e.g., via list_functions or search_functions_by_name) before trying to decompile or rename it by name.
    # ✓ For decompile_function (by name), use the full function name (e.g., name="FUN_14024DA90", or name="main").
    # ✓ For decompile_function_by_address, use the numerical address (e.g., address="14024DA90").
    # ✓ Be precise with tool selection: decompile_function is for names, decompile_function_by_address is for numerical addresses.
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
    
    # This will be the primary value loaded from MAX_STEPS env var
    max_steps: int = 5
    
    # These will also be set to the value of MAX_STEPS from env for consistency
    # if other parts of the code rely on these specific names.
    # They are now instance fields, not class-level constants.
    MAX_STEPS: int = 5 
    MAX_GOAL_STEPS: int = 5
    MAX_REVIEW_STEPS: int = 5
    
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
        # max_steps is loaded from MAX_STEPS env var, this becomes the single source of truth for step limits
        loaded_max_steps = int(os.getenv("MAX_STEPS", "5")) 
        
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
            max_steps=loaded_max_steps, # Set max_steps from env
            MAX_STEPS=loaded_max_steps, # Ensure MAX_STEPS is also set from the same env var
            MAX_GOAL_STEPS=loaded_max_steps, # Ensure MAX_GOAL_STEPS is also set from the same env var
            MAX_REVIEW_STEPS=loaded_max_steps, # Ensure MAX_REVIEW_STEPS is also set from the same env var
            cag_enabled=cag_enabled,
            cag_knowledge_cache_enabled=cag_knowledge_cache_enabled,
            cag_session_cache_enabled=cag_session_cache_enabled,
            cag_token_limit=cag_token_limit
        ) 