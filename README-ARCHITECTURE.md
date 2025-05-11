# OGhidra Simplified Architecture

This document explains the simplified three-phase architecture of OGhidra's AI bridge.

## Overview

OGhidra uses a streamlined three-phase approach to process user queries and interact with Ghidra through the GhidraMCP protocol. This architecture provides a balance between simplicity and effectiveness, making it easier to understand, modify, and extend.

## Three-Phase Architecture

The OGhidra AI bridge processes queries through three distinct phases:

### 1. Planning Phase

The planning phase is where the AI analyzes the user's query and creates a plan for addressing it.

**Key characteristics:**
- Focuses on understanding what information is needed
- Determines which Ghidra tools should be used
- Establishes a logical sequence of operations
- Does not execute any commands yet

**Output:**
- A structured plan outlining the steps to answer the query

### 2. Tool Calling Phase (Execution)

The tool calling phase is where the AI executes the necessary Ghidra commands to gather information.

**Key characteristics:**
- Executes Ghidra commands using the EXECUTE: format
- Focuses on retrieving information from the binary
- Handles error cases and provides fallbacks
- Stores command results for later analysis

**Output:**
- Raw data from Ghidra needed to answer the query

### 3. Analysis Phase

The analysis phase is where the AI interprets the results and provides a comprehensive answer.

**Key characteristics:**
- Analyzes results from the tool calling phase
- Connects different pieces of information
- Provides explanations and insights
- Formats the final response for clarity

**Output:**
- A comprehensive answer to the user's query

## Benefits of the Three-Phase Architecture

1. **Simplicity**: Easy to understand and modify
2. **Separation of Concerns**: Each phase has a clear, focused responsibility
3. **Configurability**: Each phase can use a different LLM model
4. **Reliability**: Less complex state management
5. **Extensibility**: Easy to add capabilities to specific phases

## How to Customize

Each phase can be customized through:

1. **System Prompts**: Define specific behavior for each phase
2. **Model Selection**: Use different models for different phases
3. **Error Handling**: Customize how errors are handled in each phase

See README-MODEL-SWITCHING.md for detailed information on how to configure different models for each phase.

## Implementation Details

The three-phase architecture is primarily implemented in the `Bridge.process_query()` method, with support from:

- `OllamaConfig`: Defines phase-specific system prompts and model configurations
- `OllamaClient.generate_with_phase()`: Handles model selection and prompt generation for each phase
- `CommandParser`: Extracts and processes tool commands from AI responses

This streamlined approach makes the codebase more maintainable while still providing powerful functionality for reverse engineering with Ghidra.

# Key Implementation Classes

The implementation follows an object-oriented design with the following key classes:

* `Bridge`: Main class that coordinates the multi-phase processing
* `OllamaClient`: Handles communication with the Ollama API
* `GhidraMCPClient`: Communicates with the GhidraMCP server
* `BridgeConfig`: Centralizes configuration management

# Important Methods

The key methods in this architecture include:

* `Bridge.process_query()`: Entry point that orchestrates the three phases
* `Bridge._run_planning_phase()`: Handles the planning process
* `Bridge._run_execution_phase()`: Executes tools and gathers data
* `Bridge._extract_suggestions()`: Identifies tool calls that need to be executed
* `OllamaClient.generate_with_phase()`: Handles model selection and prompt generation for each phase
* `GhidraMCPClient.execute_command()`: Executes commands on the Ghidra instance 