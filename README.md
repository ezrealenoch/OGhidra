# OGhidra - Ollama-GhidraMCP Bridge

OGhidra bridges the gap between Large Language Models (LLMs) running via Ollama and the Ghidra reverse engineering platform through the GhidraMCP API. It enables using natural language to interact with Ghidra for binary analysis tasks.

Finding Malware with the 'run-tool analyze_function()' feature
![momento-0-malwarefind](https://github.com/user-attachments/assets/2a927ada-00d6-4297-9277-5a37f98062f8)
![momento-2-malwarefind](https://github.com/user-attachments/assets/a2bba935-a138-4a2d-b5f4-7b9ac423a954)
![momento-4-malwarefind](https://github.com/user-attachments/assets/1e668b1c-14ed-4424-a0f2-6a5b2b265aba)


## Key Features

*   **Dual API Server Architecture**: Uses the original GhidraMCP server and an extended Flask-based server for comprehensive API coverage.
*   **Multi-Phase AI Processing**: Employs a Planning-Execution-Analysis workflow for structured interaction.
*   **Flexible Model Configuration**: Allows using different Ollama models for each processing phase.
*   **Command Normalization**: Improves compatibility with various LLMs by correcting command formats.
*   **Session Memory & Caching**: Features session history, Retrieval-Augmented Generation (RAG), and Cache-Augmented Generation (CAG) for contextual awareness and knowledge persistence.
*   **Interactive & Scriptable**: Can be used interactively or integrated into scripts.

## Architecture Overview

OGhidra uses a streamlined three-phase approach:

1.  **Planning Phase**: An LLM analyzes the user's query and generates a structured plan using Ghidra tools.
2.  **Tool Calling Phase (Execution)**: The plan is deterministically parsed, and the corresponding GhidraMCP client methods are called to interact with the Ghidra instance(s). This phase uses a Python function (`_parse_and_execute_plan` in `src/bridge.py`) instead of an LLM.
3.  **Analysis Phase**: An LLM analyzes the results gathered from Ghidra and provides a comprehensive response.

### Dual API Servers

*   **Original GhidraMCP Server**: Typically runs on `http://localhost:8080`. Provides core Ghidra functions.
*   **Extended API Server**: A Flask server (`src/ghidra_mcp_server.py`) running on `http://localhost:8081` (default). Implements functions defined in `ghidra_knowledge_cache/function_signatures.json`.
*   **Client Fallback**: The `GhidraMCPClient` (`src/ghidra_mcp_client.py`) attempts calls to the original server first and falls back to the extended server if needed.

### Key Implementation Classes

*   `Bridge`: Main class coordinating the multi-phase processing (`src/bridge.py`).
*   `OllamaClient`: Handles communication with the Ollama API (`src/ollama_client.py`).
*   `GhidraMCPClient`: Communicates with the GhidraMCP servers (`src/ghidra_mcp_client.py`).
*   `BridgeConfig`: Centralizes configuration management (`src/config.py`).
*   `MemoryManager`: Manages session history and RAG (`src/memory_manager.py`).
*   `CAGManager`: Manages Cache-Augmented Generation (`src/cag/manager.py`).

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd OGhidra-main
    ```
2.  **Set up Ghidra and GhidraMCP**: Follow the instructions for Ghidra and the GhidraMCP plugin to have the original server running (usually on port 8080).
3.  **Create a Python virtual environment (optional but recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate    # Windows
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Configure environment variables:**
    *   Copy `.envexample` to `.env`.
    *   Edit `.env` to set your Ollama endpoint (`OLLAMA_API_URL`), default model (`OLLAMA_MODEL`), and GhidraMCP server URLs (`GHIDRA_MCP_URL`, `GHIDRA_MCP_EXTENDED_URL`).
    *   Configure phase-specific models, memory, and CAG settings as needed (see below).

## Running OGhidra

### 1. Start the Extended API Server

```bash
python src/ghidra_mcp_server.py
```
This will start the Flask server, typically on `http://localhost:8081`.

### 2. Run the Bridge

**Interactive Mode:**

```bash
python src/main.py --interactive
```

**Single Query:**

```bash
python src/main.py "Your analysis query here"
```

## Configuration Details

Configuration is primarily managed via the `.env` file and command-line arguments.

### Models and Phases

*   Set the default model: `OLLAMA_MODEL=llama3`
*   Set phase-specific models (optional):
    *   `OLLAMA_MODEL_PLANNING=gemma3:27b`
    *   `OLLAMA_MODEL_ANALYSIS=gemma3:27b`
    *   (Note: The Execution phase uses deterministic Python code, not an LLM).
*   Use `--list-models` to see available Ollama models.
*   Phase-specific system prompts can also be set (e.g., `OLLAMA_SYSTEM_PROMPT_PLANNING`).

See `README-MODELS.md` and `README-MODEL-SWITCHING.md` (now incorporated here) for more details on model selection recommendations.

### Command Normalization

The system automatically normalizes command names (e.g., `decompileFunction` -> `decompile_function`) and parameters to improve compatibility with LLMs that don't strictly follow the required format. Normalizations are logged to the console.

See `README-COMMAND-NORMALIZATION.md` (now incorporated here) for details.

### Session Memory (History & RAG)

*   **Enable/Disable**: `SESSION_HISTORY_ENABLED=true` / `false`
*   **Storage Path**: `SESSION_HISTORY_PATH="data/ollama_ghidra_session_history.jsonl"`
*   **Max Sessions**: `SESSION_HISTORY_MAX_SESSIONS=1000`
*   **Vector Embeddings (RAG)**:
    *   `SESSION_HISTORY_USE_VECTOR_EMBEDDINGS=true` / `false`
    *   `SESSION_HISTORY_VECTOR_DB_PATH="data/vector_db"`
*   **Command Line:**
    *   `python src/main.py --check-memory`
    *   `python src/main.py --memory-stats`
    *   `python src/main.py --clear-memory`
    *   `python src/main.py --enable-vector-embeddings` / `--disable-vector-embeddings`
*   **Interactive Commands**: `memory-health`, `memory-stats`, `memory-clear`, `memory-vectors-on`, `memory-vectors-off`

See `src/README_MEMORY.md` (now incorporated here) for implementation details.

### Cache-Augmented Generation (CAG)

CAG provides persistent, cached knowledge (Ghidra commands, workflows) and session context (decompiled functions, renames) without real-time retrieval.

*   **Enable/Disable**: `CAG_ENABLED=true` / `false`
*   **Knowledge Cache**: `CAG_KNOWLEDGE_CACHE_ENABLED=true` / `false`
*   **Session Cache**: `CAG_SESSION_CACHE_ENABLED=true` / `false`
*   **Token Limit**: `CAG_TOKEN_LIMIT=2000`
*   **Command Line**: `python src/main.py --disable-cag`
*   **Interactive Command**: `cag` (shows status)

Knowledge Base Files:
*   `ghidra_knowledge_cache/function_signatures.json`
*   `ghidra_knowledge_cache/common_workflows.json` (if exists)
*   `ghidra_knowledge_cache/binary_patterns.json` (if exists)
*   `ghidra_knowledge_cache/analysis_rules.json` (if exists)

See `README-CAG.md` (now incorporated here) for more details.

## Testing

*   **Extended API Server Tests**: `python -m unittest src/test_extended_api.py` (Ensure the extended server is running).
*   **Bridge/Normalization Tests**: Check `tests/` directory (e.g., `test_command_normalization.py`, `test_bridge.py`). Run relevant tests using `unittest`.
*   **Memory Sample Data**: `python src/generate_sample_data.py` (See memory docs for options).

## Contributing

Please refer to the project's contribution guidelines (if available).

## License

Specify project license here.
