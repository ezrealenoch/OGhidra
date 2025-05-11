# Using Different Models for Different Phases

The Ollama-GhidraMCP Bridge supports using different models for each phase of the analysis process. This allows you to optimize the model selection for each specific task.

## Phases

The bridge operates in three main phases:

1. **Planning Phase**: The model plans how to analyze the binary file and determine which tools to use based on the user's request.
2. **Execution Phase**: The model executes Ghidra commands to gather information about the binary.
3. **Analysis Phase**: The model analyzes the gathered information and provides a final response to the user.

## Configuring Models

You can configure which model to use for each phase by setting environment variables:

```
# Default model (used for any phase without a specific model assigned)
OLLAMA_MODEL=llama3.1

# Phase-specific models
OLLAMA_MODEL_PLANNING=gemma3:27b    # Model for the planning phase
OLLAMA_MODEL_EXECUTION=gemma3:27b    # Model for executing tools/commands
OLLAMA_MODEL_ANALYSIS=qwen3:30b-a3b   # Model for analyzing results
```

These variables can be set in a `.env` file in the project root directory. See `.envexample` for a template.

## Model Capabilities

Not all models support all features. Specifically, tool calling (used for executing Ghidra commands) requires a model that supports the Ollama chat API with function calling.

### Models Known to Support Tool Calling

* llama3.1 (recommended)
* llama4
* codellama

### Handling of Incompatible Models

If you specify a model that doesn't support tool calling for the execution phase, the bridge will:

1. First try to use the chat API with tools
2. If that fails (usually with a 400 Bad Request), it will remember that this model doesn't support tool calling
3. Fall back to using the generate API, which can still work but may produce less reliable tool execution

## Recommendations

* For best results with tool calling, use **llama3.1** or **llama4** for the execution phase.
* For planning and analysis phases, you can use a broader range of models based on their strengths.
* If you're unsure, use the same capable model for all phases.

## Example Configurations

### Balanced Performance

```
OLLAMA_MODEL=llama3.1
```

### Optimized for Different Strengths

```
OLLAMA_MODEL=llama3.1
OLLAMA_MODEL_PLANNING=gemma3:27b
OLLAMA_MODEL_EXECUTION=llama3.1
OLLAMA_MODEL_ANALYSIS=qwen3:30b-a3b
```

### Maximum Quality (Larger Models)

```
OLLAMA_MODEL=llama4:latest
OLLAMA_MODEL_PLANNING=llama4:latest
OLLAMA_MODEL_EXECUTION=llama4:latest
OLLAMA_MODEL_ANALYSIS=llama4:latest
``` 