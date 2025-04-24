# Ollama-GhidraMCP Bridge (Google-ADK WIP)

A Python application that bridges locally hosted AI models (via Ollama) with GhidraMCP for AI-assisted reverse engineering tasks within Ghidra.

![Screenshot 2025-04-14 155639](https://github.com/user-attachments/assets/f8fb0fb1-6a9c-4097-8e3e-00d87d2d96f4)


## Architecture

This bridge connects the following components:

- **Ollama Server**: Hosts local AI models (e.g., LLaMA 3, Mistral) accessible via REST API
- **Bridge Application**: This Python application that serves as an intermediary
- **GhidraMCP Server**: Exposes Ghidra's functionalities via MCP

## Features

- **Natural Language Queries**: Translate user queries into GhidraMCP commands (via direct script or ADK agent).
- **Context Management**: Maintains conversation context for multi-step analyses
- **Interactive Mode**: Command-line interface for interactive sessions using the original bridge logic.
- **Health Checks**: Verify connectivity to Ollama and GhidraMCP services
- **(New) ADK Agent Workflow**: An experimental agent loop (`ghidra_analyzer`) using Google ADK for structured planning, tool execution, analysis, and review of Ghidra tasks.

## Requirements

- Python 3.8+
- Ollama server running locally or remotely
- GhidraMCP server running within Ghidra
- Google ADK (`pip install google-adk`)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ollama-ghidra-bridge.git
   cd ollama-ghidra-bridge
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file by copying the example (optional, can use defaults):
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file if you need to override default Ollama (`OLLAMA_MODEL`, `OLLAMA_API_BASE`) or GhidraMCP (`GHIDRA_MCP_URL`) settings.

## Usage

### Option 1: Original Interactive Bridge (Command Line)

Run the original bridge script in interactive mode:

```bash
python main.py --interactive
```

Special commands:
- Type `exit` or `quit` to exit
- Type `health` to check connectivity to Ollama and GhidraMCP

**Mock Mode:**

If you don't have a GhidraMCP server running or want to test the bridge functionality:

```bash
python main.py --interactive --mock
```

**Single Query:**

```bash
echo "What functions are in this binary?" | python main.py
```

### Option 2: ADK Ghidra Analyzer Agent (Web Interface)

This uses the Google Agent Development Kit (ADK) to run a more structured agent loop.

**Prerequisites:**

1. **Ensure GhidraMCP server is running** inside your Ghidra instance.
2. **Ensure Ollama server is running** (e.g., `ollama serve` if not running as a service) and the model specified in `.env` or the default (`cogito:32b`) is pulled (`ollama pull cogito:32b`).

**Run the ADK Web UI:**

From the project root directory (`OGhidra-main`):

```bash
adk web
```

- Open your browser to `http://localhost:8000`.
- Select the `ghidra_analyzer` agent from the dropdown menu.
- Enter your query (e.g., "List the functions", "Decompile main", "Find the function at 0x401000 and rename it to process_data").
- Observe the agent loop through Planning, Executing Ghidra tools, Analyzing results, and Reviewing progress.

**How the ADK Agent Works:**

1. **Planner:** Analyzes your query and creates a plan of Ghidra tool calls.
2. **Executor:** Runs the next tool call from the plan against the GhidraMCP server.
3. **Analyzer:** Interprets the tool's result.
4. **Reviewer:** Checks if the plan is complete and the query is answered. If yes, it stops; otherwise, the loop continues.

### Configuration Options

Configure the bridge and ADK agent through:

1. Environment variables (see `.env.example` for `OLLAMA_*` and `GHIDRA_*` variables).
2. Command line arguments for the *original* bridge (`main.py --interactive ...`).

## Troubleshooting

### GhidraMCP Connection Issues

If you encounter 404 errors or empty responses from the GhidraMCP server:

1. **Verify GhidraMCP server is running**: Make sure the GhidraMCP server script (`bridge_mcp_ghidra.py`) is running within Ghidra and accessible. Test with `curl http://localhost:8080/list_functions` (or your configured URL).
2. **Check server URL**: Ensure the `GHIDRA_MCP_URL` in your environment/`.env` file (or the default `http://localhost:8080`) is correct, including the port.
3. **Try mock mode** (`main.py --mock`) for the original bridge to isolate issues.

### Ollama API Issues

If you encounter issues with the Ollama API:

1. Ensure Ollama is running: `curl http://localhost:11434` (or your configured URL).
2. Verify the model specified exists: `ollama list`.
3. Check the `OLLAMA_API_BASE` environment variable if not using the default.

### ADK Agent Issues

- **`ImportError`**: Ensure you run `pip install -r requirements.txt` from the project root.
- **Tool Execution Errors**: Check the `adk web` console output for detailed error messages from the Ghidra tools or the agents. Ensure GhidraMCP is running and accessible.
- **Planning/Looping Issues**: The LLM might struggle with complex plans or interpreting results. Try simplifying your query or adjusting agent instructions in `src/adk_agents/ghidra_analyzer/agents.py`.

### JSON Parsing Errors

If you see "Expecting value" or other JSON parsing errors (less likely with the ADK agent):

1. The API might be returning empty or non-JSON responses.
2. Try running with `LOG_LEVEL=DEBUG` environment variable for more detailed logs.
3. Check the API documentation to ensure proper request format.

## Available GhidraMCP Commands (for reference)

*These are the underlying commands the ADK tools wrap.*

- `list_functions()`: Retrieve a list of all functions.
- `decompile(function_name)`: Decompile a function by name (POST request).
- `decompile_function(address)`: Decompile function at address (GET request).
- `rename_function_by_address(function_address, new_name)`: Rename function by address.
- `set_decompiler_comment(address, comment)`: Add comments to pseudocode.
- `set_disassembly_comment(address, comment)`: Add comments to disassembly.
- `get_current_address()`: Get address selected in UI.
- `get_current_function()`: Get function selected in UI.
- *Many others are available in `src/ghidra_client.py` and could be wrapped as ADK tools.* 

## Example Queries (for ADK Agent)

- "List all functions in this binary"
- "Decompile the function at address 0x1000"
- "Find the function named 'entry' and decompile it"
- "Add a comment 'Check buffer size here' at address 0x401550 in the decompiler"
- "What function is currently selected? Decompile it."

## License

[MIT License](LICENSE)

## Acknowledgements

- [LaurieWired/GhidraMCP](https://github.com/LaurieWired/GhidraMCP) - GhidraMCP server
- [Ollama](https://ollama.ai/) - Local large language model hosting
- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)

# Google ADK Loop Agent Examples

This repository contains examples of Google Agent Development Kit (ADK) Loop Agents.

## Examples

### Document Improvement Demo

A simple implementation of a loop agent that iteratively improves a document through a cycle of writing and critique.

- Located in: `loop_demo/`
- Based on the [official example](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/#full-example-iterative-document-improvement)

## Getting Started

### Installation

1. Install the Google ADK package:

```bash
pip install google-adk
```

2. Set up your API key in the `.env` file:

```bash
# In loop_demo/.env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

### Running the Examples

#### Web Interface

```bash
adk web
```

Then open http://localhost:8000 in your browser and select the desired agent from the dropdown.

#### Command Line

```bash
# Document Improvement Demo
python -m loop_demo.cli --topic "Your Topic Here"
```

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Loop Agents Documentation](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)

# OGhidra - Agentic Ghidra Analysis

OGhidra integrates Google's Agent Development Kit (ADK) with the Ghidra Software Reverse Engineering Framework, enhancing Ghidra's capabilities through an agentic workflow for binary analysis.

## Project Structure

```
├── src/
│   ├── adk_agents/
│   │   ├── ghidra_analyzer/
│   │   │   ├── agents.py        # Defines the Ghidra analyzer agents
│   │   │   ├── tests.py         # Test suite for Ghidra analyzer
│   │   │   └── run_tests.py     # Script to run the tests
│   ├── adk_tools/
│   │   ├── ghidra_mcp.py        # Defines Ghidra ADK tools
│   │   └── ...
│   └── ...
```

## Setup

### Prerequisites

- Python 3.10+
- Google ADK (`pip install google-adk`)
- LiteLLM (`pip install litellm`)
- Ghidra (with GhidraMCP server running)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/OGhidra.git
cd OGhidra
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
- Set up your LLM API keys in an `.env` file
- Configure GhidraMCP server (ensure it's running)

## Usage

### Starting the ADK Web Interface

Run the ADK web interface to interact with the Ghidra analyzer agents:

```bash
cd OGhidra
adk web
```

This will start the web interface at http://localhost:8000

### Opening a Project in Ghidra

1. Open Ghidra and load your binary
2. Start the MCP server from Ghidra's menu: Window -> MCP Server
3. The server will start on localhost:2468 by default

### Example Queries

The Ghidra analyzer supports various types of queries:

- **List all functions**:
  ```
  List all functions in the current binary
  ```

- **Analyze a specific function**:
  ```
  What does the function main do?
  ```

- **Recursive function analysis**:
  ```
  Analyze the program starting from entry point and describe its behavior
  ```

- **Function renaming based on behavior**:
  ```
  Rename function FUN_00401000 based on its behavior
  ```

### Running Tests

OGhidra includes comprehensive tests for the Ghidra analyzer agent. To run the test suite:

```bash
cd OGhidra/src/adk_agents/ghidra_analyzer
python run_tests.py
```

The test suite includes:
- Unit tests for all Ghidra tools
- Mock responses to simulate GhidraMCP server
- Tests for agent interactions and workflows

## Architecture

OGhidra implements an agent loop with four specialized agents:

1. **Planning Agent**: Analyzes user queries and creates a plan for binary analysis
2. **Tool Execution Agent**: Executes Ghidra analysis tools based on the plan
3. **Analysis Agent**: Interprets results from tool execution
4. **Review Agent**: Provides final summaries and recommendations

## Troubleshooting

- **MCP Connection Issues**: Ensure the MCP server is running in Ghidra (Window -> MCP Server)
- **ADK Errors**: Check that your `.env` file contains the required API keys
- **Missing Agent Functions**: Verify that all Python packages are properly installed
- **Test Failures**: If tests fail, check your environment setup and GhidraMCP server status

## Extending the System

You can add additional Ghidra tools by editing `src/adk_tools/ghidra_mcp.py` and updating the agent definitions in `src/adk_agents/ghidra_analyzer/agents.py`.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The Ghidra team at NSA for their amazing reverse engineering framework
- Google ADK team for the agent framework
