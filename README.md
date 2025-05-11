# Ollama-GhidraMCP Bridge

A Python application that bridges locally hosted AI models (via Ollama) with GhidraMCP for AI-assisted reverse engineering tasks within Ghidra.
(Working with multiple models including llama3, codellama, and now Gemma. Default is currently gemma3:27b)
![Screenshot 2025-04-14 155639](https://github.com/user-attachments/assets/f8fb0fb1-6a9c-4097-8e3e-00d87d2d96f4)


## Architecture

This bridge connects the following components:

- **Ollama Server**: Hosts local AI models (e.g., LLaMA 3, Mistral, Gemma) accessible via REST API
- **Bridge Application**: This Python application that serves as an intermediary
- **GhidraMCP Server**: Exposes Ghidra's functionalities via MCP

## Features

- **Natural Language Queries**: Translate user queries into GhidraMCP commands
- **Context Management**: Maintains conversation context for multi-step analyses
- **Interactive Mode**: Command-line interface for interactive sessions
- **Health Checks**: Verify connectivity to Ollama and GhidraMCP services
- **Model Switching**: Use different models for different phases of the agentic loop
- **Agentic Capabilities**: Multi-step reasoning with planning, execution, and analysis phases
- **Terminal Output**: View tool calls and results directly in the terminal
- **Command Normalization**: Automatically convert camelCase to snake_case for non-tool-calling models
- **Enhanced Error Messages**: Clear feedback for incorrect command formats

## Requirements

- Python 3.8+
- Ollama server running locally or remotely
- GhidraMCP server running within Ghidra

## Pre-installation
- Follow the installation steps from Laurie's project (https://github.com/LaurieWired/GhidraMCP)
   - Install the GhidraPlugin and enable developer mode

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/ezrealenoch/ollama-ghidra-bridge.git
   cd ollama-ghidra-bridge
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file by copying the example:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file to configure your Ollama and GhidraMCP settings.

## Usage

### Interactive Mode

Run the bridge in interactive mode:

```bash
python main.py --interactive
```

Special commands:
- Type `exit` or `quit` to exit
- Type `health` to check connectivity to Ollama and GhidraMCP
- Type `models` to list available Ollama models

### Model Switching for Agentic Loop

You can now use different models for different phases of the agentic reasoning loop. This allows you to optimize the use of models based on their strengths:

```bash
python main.py --interactive --model llama3 --planning-model llama3 --execution-model codellama:7b
```

The bridge now also supports **Gemma models**:

```bash
python main.py --interactive --model gemma3:27b
```

Available phase-specific models:
- `--planning-model`: Model for the planning phase (creating analysis plans)
- `--execution-model`: Model for the execution phase (running tools)
- `--analysis-model`: Model for the analysis phase (evaluating results)

You can also configure these via environment variables:
```
OLLAMA_MODEL_PLANNING=llama3
OLLAMA_MODEL_EXECUTION=codellama:7b
OLLAMA_MODEL_ANALYSIS=llama3:34b
```

For more detailed information about model switching, see [README-MODEL-SWITCHING.md](README-MODEL-SWITCHING.md).

### Non-Tool-Calling Models

For models like Gemma that don't support the Ollama tool-calling API, the bridge includes:

1. **Command normalization**: Automatically converts camelCase to snake_case (e.g., `getCurrentFunction` → `get_current_function`)
2. **Parameter name standardization**: Handles common parameter errors (e.g., `function_address` → `address`)
3. **Enhanced error messages**: Provides clear guidance when errors occur
4. **Terminal output**: Shows command execution output directly in the terminal

### Mock Mode

If you don't have a GhidraMCP server running or want to test the bridge functionality, you can use mock mode:

```bash
python main.py --interactive --mock
```

In mock mode, the bridge simulates GhidraMCP responses without contacting the actual server.

### Command Line Mode

Process a single query:

```bash
echo "What functions are in this binary?" | python main.py
```

### Configuration Options

You can configure the bridge through:

1. Environment variables (see `.env.example`)
2. Command line arguments:
   ```bash
   python main.py --ollama-url http://localhost:11434 --ghidra-url http://localhost:8080 --model gemma3:27b --interactive
   ```

## Troubleshooting

### GhidraMCP Connection Issues

If you encounter 404 errors or empty responses from the GhidraMCP server:

1. **Verify GhidraMCP server is running**: Make sure the GhidraMCP server is running and accessible. You can test with `curl http://localhost:8080/methods`

2. **Check endpoint structure**: This bridge directly implements the same endpoint structure as the [GhidraMCP repository](https://github.com/LaurieWired/GhidraMCP/blob/main/bridge_mcp_ghidra.py).

3. **Try mock mode**: Use the `--mock` flag to verify the bridge functionality without connecting to a real server.

4. **Check server URL**: Ensure the server URL in your configuration is correct, including the port.

### Command Format Issues

If your model is having trouble with command formats:

1. Make sure your query explicitly states the command in the format: `EXECUTE: command_name(param="value")`
2. For string parameters, always use quotes: `name="function_name"` 
3. Use snake_case for command names: `get_current_function()` not `getCurrentFunction()`
4. Check terminal output for error messages about incorrect command formats

### Ollama API Issues

If you encounter issues with the Ollama API:

1. Ensure Ollama is running: `curl http://localhost:11434`
2. Verify the model specified exists: `ollama list`
3. Check the model compatibility with the prompt format

### JSON Parsing Errors

If you see "Expecting value" or other JSON parsing errors:

1. The API might be returning empty or non-JSON responses
2. Try running with `LOG_LEVEL=DEBUG` for more detailed logs
3. Check the API documentation to ensure proper request format

## Available GhidraMCP Commands

The bridge supports the following commands:

- `decompile_function(name="function_name")`: Decompile a function by name
- `decompile_function_by_address(address="0x1000")`: Decompile a function at a given address
- `rename_function(old_name="FUN_1000", new_name="initialize_data")`: Rename a function
- `rename_function_by_address(address="0x1000", new_name="initialize_data")`: Rename a function by address
- `list_functions()`: Retrieve a list of all functions in the binary
- `search_functions_by_name(query="init")`: Search for functions by substring
- `list_imports()`: List all imported functions
- `list_exports()`: List all exported functions
- `list_segments()`: Retrieve the memory layout of the binary

## Example Queries

- "List all functions in this binary"
- "Decompile the function at address 0x1000"
- "What's the memory layout of this binary?"
- "Find all strings containing 'password'"
- "Rename the function at 0x2000 to 'process_data'"

## License

[MIT License](LICENSE)

## Acknowledgements

- [LaurieWired/GhidraMCP](https://github.com/LaurieWired/GhidraMCP) - GhidraMCP server
- [Ollama](https://ollama.ai/) - Local large language model hosting 
