# Ollama-GhidraMCP Bridge

A Python application that bridges locally hosted AI models (via Ollama) with GhidraMCP for AI-assisted reverse engineering tasks within Ghidra.
(Working on agentic loop. Currently using cogito:32b, its very brief and not wordy so its good at running tools)
![Screenshot 2025-04-14 155639](https://github.com/user-attachments/assets/f8fb0fb1-6a9c-4097-8e3e-00d87d2d96f4)


## Architecture

This bridge connects the following components:

- **Ollama Server**: Hosts local AI models (e.g., LLaMA 3, Mistral) accessible via REST API
- **Bridge Application**: This Python application that serves as an intermediary
- **GhidraMCP Server**: Exposes Ghidra's functionalities via MCP

## Features

- **Natural Language Queries**: Translate user queries into GhidraMCP commands
- **Context Management**: Maintains conversation context for multi-step analyses
- **Interactive Mode**: Command-line interface for interactive sessions
- **Health Checks**: Verify connectivity to Ollama and GhidraMCP services
- **Specialized Summarization Model**: Use a separate model optimized for generating comprehensive reports
- **Model Switching**: Use different models for different phases of the agentic loop
- **Agentic Capabilities**: Multi-step reasoning with planning, execution, review, and learning phases

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

Available phase-specific models:
- `--planning-model`: Model for the planning phase (creating analysis plans)
- `--execution-model`: Model for the execution phase (running tools)
- `--review-model`: Model for the review phase (evaluating results)
- `--verification-model`: Model for the verification phase
- `--learning-model`: Model for the learning phase
- `--summarization-model`: Model for summarization tasks

You can also configure these via environment variables:
```
OLLAMA_MODEL_PLANNING=llama3
OLLAMA_MODEL_EXECUTION=codellama:7b
```

For more detailed information about model switching, see [README-MODEL-SWITCHING.md](README-MODEL-SWITCHING.md).

### Using the Specialized Summarization Model

You can configure a separate model specifically for summarization and report generation tasks:

```bash
python main.py --interactive --model llama3 --summarization-model mixtral:8x7b
```

The summarization model will be used for:
1. Generating final reports when analysis is complete
2. Summarizing long conversation contexts
3. Processing queries that specifically ask for summaries or reports

You can also set this in your `.env` file:
```
OLLAMA_MODEL=llama3
OLLAMA_SUMMARIZATION_MODEL=mixtral:8x7b
```

This is particularly useful when you want to use:
- A lightweight model for interactive analysis and tool execution
- A more powerful model for creating comprehensive, well-structured reports

The system automatically detects summarization/report requests by looking for keywords like "summarize", "report", "analyze the results", etc.

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
   python main.py --ollama-url http://localhost:11434 --ghidra-url http://localhost:8080 --model llama3 --interactive
   ```

## Troubleshooting

### GhidraMCP Connection Issues

If you encounter 404 errors or empty responses from the GhidraMCP server:

1. **Verify GhidraMCP server is running**: Make sure the GhidraMCP server is running and accessible. You can test with `curl http://localhost:8080/methods`

2. **Check endpoint structure**: This bridge directly implements the same endpoint structure as the [GhidraMCP repository](https://github.com/LaurieWired/GhidraMCP/blob/main/bridge_mcp_ghidra.py).

3. **Try mock mode**: Use the `--mock` flag to verify the bridge functionality without connecting to a real server.

4. **Check server URL**: Ensure the server URL in your configuration is correct, including the port.

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

- `decompile_function(address)`: Decompile a function at a given address
- `rename_function(address, name)`: Rename a function to a specified name
- `list_functions()`: Retrieve a list of all functions in the binary
- `get_imports()`: List all imported functions
- `get_exports()`: List all exported functions
- `get_memory_map()`: Retrieve the memory layout of the binary
- `comment_function(address, comment)`: Add comments to a function
- `rename_variable(function_address, variable_name, new_name)`: Rename a local variable
- `search_strings(pattern)`: Search for strings in memory
- `get_references(address)`: Get references from/to a specific address

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
