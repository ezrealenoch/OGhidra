# Ollama-GhidraMCP Bridge

A Python application that bridges locally hosted AI models (via Ollama) with GhidraMCP for AI-assisted reverse engineering tasks within Ghidra.
(Authors Note: LOL I asked it to be agentic and it worked. Currently using cogito:32b, its very brief and not wordy so its good at running tools)
![Screenshot 2025-04-14 155639](https://github.com/user-attachments/assets/f8fb0fb1-6a9c-4097-8e3e-00d87d2d96f4)


## Architecture

<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 1000 800" xmlns="http://www.w3.org/2000/svg">
  <!-- Background and Title -->
  <rect width="1000" height="800" fill="#f8f9fa" rx="10" ry="10"/>
  <text x="500" y="40" font-family="Arial, sans-serif" font-size="24" font-weight="bold" text-anchor="middle" fill="#333">OGhidra-Special-Agentivity: Agentic Architecture</text>
  
  <!-- External Systems -->
  <rect x="40" y="100" width="920" height="120" rx="8" ry="8" fill="#f9f6e5" stroke="#d9a74a" stroke-width="2"/>
  <text x="500" y="125" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="#333">External Systems</text>
  
  <!-- Ollama Server -->
  <rect x="100" y="145" width="200" height="60" rx="5" ry="5" fill="#f8d7a9" stroke="#d9a74a" stroke-width="2"/>
  <text x="200" y="165" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Ollama Server</text>
  <text x="200" y="185" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#333">(Local LLM Host)</text>
  
  <!-- Ghidra Server -->
  <rect x="700" y="145" width="200" height="60" rx="5" ry="5" fill="#f8d7a9" stroke="#d9a74a" stroke-width="2"/>
  <text x="800" y="165" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Ghidra MCP Server</text>
  <text x="800" y="185" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#333">(Reverse Engineering)</text>
  
  <!-- Bridge Layer -->
  <rect x="40" y="240" width="920" height="120" rx="8" ry="8" fill="#e3f2fd" stroke="#90caf9" stroke-width="2"/>
  <text x="500" y="265" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="#333">Bridge Application</text>
  
  <!-- Bridge Components -->
  <rect x="80" y="285" width="130" height="60" rx="5" ry="5" fill="#bbdefb" stroke="#64b5f6" stroke-width="2"/>
  <text x="145" y="310" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Main App</text>
  <text x="145" y="325" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#333">(main.py)</text>
  
  <rect x="240" y="285" width="130" height="60" rx="5" ry="5" fill="#bbdefb" stroke="#64b5f6" stroke-width="2"/>
  <text x="305" y="310" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Bridge Component</text>
  <text x="305" y="325" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#333">(src/bridge.py)</text>
  
  <rect x="400" y="285" width="130" height="60" rx="5" ry="5" fill="#bbdefb" stroke="#64b5f6" stroke-width="2"/>
  <text x="465" y="310" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Command Parser</text>
  <text x="465" y="325" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#333">(command_parser.py)</text>
  
  <rect x="560" y="285" width="130" height="60" rx="5" ry="5" fill="#bbdefb" stroke="#64b5f6" stroke-width="2"/>
  <text x="625" y="310" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Ollama Client</text>
  <text x="625" y="325" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#333">(ollama_client.py)</text>
  
  <rect x="720" y="285" width="130" height="60" rx="5" ry="5" fill="#bbdefb" stroke="#64b5f6" stroke-width="2"/>
  <text x="785" y="310" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Ghidra Client</text>
  <text x="785" y="325" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#333">(ghidra_client.py)</text>
  
  <!-- Agent System -->
  <rect x="40" y="380" width="920" height="380" rx="8" ry="8" fill="#e8f5e9" stroke="#81c784" stroke-width="2"/>
  <text x="500" y="405" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="#333">Agent System</text>
  
  <!-- Agent Factory -->
  <rect x="80" y="430" width="160" height="60" rx="5" ry="5" fill="#fff9c4" stroke="#fdd835" stroke-width="2"/>
  <text x="160" y="450" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Agent Factory</text>
  <text x="160" y="470" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#333">(agent_factory.py)</text>
  
  <!-- Reasoning Layer -->
  <rect x="80" y="510" width="240" height="180" rx="8" ry="8" fill="#c8e6c9" stroke="#66bb6a" stroke-width="2"/>
  <text x="200" y="530" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Reasoning Layer</text>
  
  <rect x="100" y="545" width="200" height="50" rx="5" ry="5" fill="#a5d6a7" stroke="#4caf50" stroke-width="1.5"/>
  <text x="200" y="575" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Agent Logic</text>
  
  <rect x="100" y="605" width="90" height="50" rx="5" ry="5" fill="#a5d6a7" stroke="#4caf50" stroke-width="1.5"/>
  <text x="145" y="635" font-family="Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle" fill="#333">Memory</text>
  
  <rect x="200" y="605" width="100" height="50" rx="5" ry="5" fill="#a5d6a7" stroke="#4caf50" stroke-width="1.5"/>
  <text x="250" y="635" font-family="Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle" fill="#333">LLM Client</text>
  
  <!-- Action Layer -->
  <rect x="380" y="510" width="240" height="180" rx="8" ry="8" fill="#ffccbc" stroke="#ff8a65" stroke-width="2"/>
  <text x="500" y="530" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Action Layer</text>
  
  <rect x="400" y="570" width="200" height="60" rx="5" ry="5" fill="#ffab91" stroke="#ff7043" stroke-width="1.5"/>
  <text x="500" y="595" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Action Orchestrator</text>
  <text x="500" y="615" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#333">(Manages tool invocation)</text>
  
  <!-- Tool Layer -->
  <rect x="680" y="510" width="240" height="180" rx="8" ry="8" fill="#bbdefb" stroke="#64b5f6" stroke-width="2"/>
  <text x="800" y="530" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Tool Layer</text>
  
  <rect x="700" y="545" width="200" height="50" rx="5" ry="5" fill="#90caf9" stroke="#2196f3" stroke-width="1.5"/>
  <text x="800" y="575" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Ghidra Tools</text>
  
  <rect x="700" y="605" width="200" height="50" rx="5" ry="5" fill="#90caf9" stroke="#2196f3" stroke-width="1.5"/>
  <text x="800" y="635" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Data Transformer</text>
  
  <!-- Thought-Action-Observation Loop -->
  <ellipse cx="500" cy="745" rx="220" ry="40" fill="#e1bee7" stroke="#ba68c8" stroke-width="2"/>
  <text x="500" y="740" font-family="Arial, sans-serif" font-size="15" font-weight="bold" text-anchor="middle" fill="#333">Thought → Action → Observation</text>
  <text x="500" y="760" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#333">Agent Execution Loop</text>
  
  <!-- Key Relationships Box - Perfect positioning -->
  <rect x="700" y="410" width="250" height="90" rx="5" ry="5" fill="white" stroke="#333" stroke-width="1" fill-opacity="0.9"/>
  <text x="825" y="430" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Key Relationships</text>
  <text x="720" y="455" font-family="Arial, sans-serif" font-size="12" fill="#333">• Agent Factory creates all components</text>
  <text x="720" y="475" font-family="Arial, sans-serif" font-size="12" fill="#333">• Reasoning layer makes decisions</text>
  <text x="720" y="495" font-family="Arial, sans-serif" font-size="12" fill="#333">• Action layer coordinates tool execution</text>
</svg>

This bridge connects the following components:

- **Ollama Server**: Hosts local AI models (e.g., LLaMA 3, Mistral) accessible via REST API
- **Bridge Application**: This Python application that serves as an intermediary
- **GhidraMCP Server**: Exposes Ghidra's functionalities via MCP
- **Agentic AI System**: Autonomous agent for application behavior analysis (new!)

## Features

- **Natural Language Queries**: Translate user queries into GhidraMCP commands
- **Context Management**: Maintains conversation context for multi-step analyses
- **Interactive Mode**: Command-line interface for interactive sessions
- **Health Checks**: Verify connectivity to Ollama and GhidraMCP services
- **Agentic Analysis**: Autonomous agent for analyzing application behavior (new!)

## Requirements

- Python 3.8+
- Ollama server running locally or remotely
- GhidraMCP server running within Ghidra

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

3. Create a `.env` file by copying the example:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file to configure your Ollama and GhidraMCP settings.

## Usage

### Interactive Bridge Mode

Run the bridge in interactive mode:

```bash
python main.py bridge --interactive
```

Special commands:
- Type `exit` or `quit` to exit
- Type `health` to check connectivity to Ollama and GhidraMCP

### Mock Mode

If you don't have a GhidraMCP server running or want to test the bridge functionality, you can use mock mode:

```bash
python main.py bridge --interactive --mock
```

In mock mode, the bridge simulates GhidraMCP responses without contacting the actual server.

### Command Line Mode

Process a single query:

```bash
echo "What functions are in this binary?" | python main.py bridge
```

### Agentic Analysis (New!)

The new agentic AI system can autonomously analyze application behavior:

```bash
python main.py agent --analyze --task "Analyze the behavior of this application" --iterations 15 --verbose
```

Options:
- `--analyze`: Run the analysis process
- `--task`: Description of the analysis task
- `--iterations`: Maximum number of iterations for the agent (default: 15)
- `--verbose`: Print detailed progress information

The agent will analyze the application following a Thought-Action-Observation loop and produce a comprehensive report detailing the application's behavior.

### Configuration Options

You can configure the bridge through:

1. Environment variables (see `.env.example`)
2. Command line arguments:
   ```bash
   python main.py bridge --ollama-url http://localhost:11434 --ghidra-url http://localhost:8080 --model llama3 --interactive
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
