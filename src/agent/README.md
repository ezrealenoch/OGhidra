# Agentic AI for Application Behavior Analysis

This module implements an agentic AI system for analyzing the behavior of applications by interacting with a Ghidra server within the OGHidra project. The system leverages open-source models hosted locally to provide autonomous decision-making and action execution in the analysis process.

## Architecture

The agent implementation follows a layered architecture:

1. **Tool Layer**: Abstracts the Ghidra server functionalities into tools that the Reasoning Layer can understand and utilize.
   - `GhidraTools`: Provides methods for interacting with Ghidra
   - `DataTransformer`: Transforms data between the Tool Layer and Reasoning Layer

2. **Reasoning Layer**: Houses the core intelligence of the agent.
   - `LLMClient`: Interacts with the local LLM model
   - `AgentLogic`: Manages the agent's decision-making process using a Thought-Action-Observation loop
   - `AgentMemory`: Maintains context across multiple tool invocations and analysis steps

3. **Action Layer**: Acts as an intermediary between the Reasoning Layer and the Tool Layer.
   - `ActionOrchestrator`: Handles tool invocation, result handling, and user interaction

## Usage

The agent can be used via the command line interface:

```bash
python main.py agent --analyze --task "Analyze the behavior of this application" --iterations 15 --verbose
```

### Options:

- `--analyze`: Run the analysis process
- `--task`: Description of the analysis task (default: "Analyze the behavior of the current application")
- `--iterations`: Maximum number of iterations for the agent (default: 15)
- `--verbose`: Print detailed progress information

## Internal Workflow

The agent follows a Thought-Action-Observation loop:

1. **Observation**: The agent observes the initial state of the application (e.g., function list)
2. **Thought**: Based on observations and its goals, the agent thinks about the next step
3. **Action**: The agent decides to use a specific tool to gather more information
4. **Observation**: The agent observes the results of the tool execution
5. **Repeat**: Steps 2-4 are repeated iteratively until a conclusion is reached
6. **Analysis**: The agent synthesizes its findings and generates a report

## Example Report

The agent will produce a detailed report analyzing the application's behavior, including:

- Main purpose of the application
- Key functionalities
- Potentially suspicious or malicious behaviors
- Overall architecture and flow of the application