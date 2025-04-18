# Model Switching for OGhidra

This document explains how to use the model switching feature in OGhidra, which allows you to use different Ollama models for different phases of the agentic loop.

## Overview

OGhidra's AI bridge now supports using different models for different phases of the agentic loop. This allows you to:

1. Use a larger, more capable model for planning and reasoning
2. Use a smaller, faster model for execution phases
3. Customize models for specific tasks like summarization or verification
4. Experiment with models that excel at different aspects of the reverse engineering workflow

## Phases of the Agentic Loop

The bridge's agentic loop consists of several phases, each of which can use a different model:

- **Planning**: Initial planning phase where the AI creates a plan of action
- **Execution**: Main phase where tools are executed and analysis is performed
- **Review**: Phase where the AI reviews its work and decides if more analysis is needed
- **Verification**: Phase to verify the final results
- **Learning**: Phase where patterns are identified for future analysis
- **Summarization**: Special phase for context summarization (not a standard phase, but uses the summarization model)

## Configuration Methods

### Command Line Arguments

You can specify different models for each phase using command line arguments:

```bash
python -m src.bridge --model llama3 --planning-model llama3:8b --execution-model codellama:7b --review-model mistral:7b --summarization-model llama3
```

To list all available models:

```bash
python -m src.bridge --list-models
```

### Environment Variables

You can also configure models using environment variables:

```bash
export OLLAMA_MODEL=llama3
export OLLAMA_MODEL_PLANNING=llama3:8b
export OLLAMA_MODEL_EXECUTION=codellama:7b
export OLLAMA_MODEL_REVIEW=mistral:7b
export OLLAMA_SUMMARIZATION_MODEL=llama3
```

## Example Configurations

### Fast Analysis Configuration

For quick analysis where you want a balance of performance and accuracy:

```bash
python -m src.bridge --model llama3:7b --planning-model llama3 --execution-model llama3:7b --review-model llama3
```

### Deep Analysis Configuration

For deeper analysis where you want maximum reasoning capabilities:

```bash
python -m src.bridge --model llama3 --planning-model llama3 --execution-model llama3 --review-model llama3 --verification-model llama3
```

### Mixed Capability Configuration

Using specialized models for different phases:

```bash
python -m src.bridge --model llama3:7b --planning-model llama3 --execution-model codellama:7b --review-model mistral --verification-model llama3
```

## System Prompts for Different Phases

You can also customize the system prompts for different phases using environment variables:

```bash
export OLLAMA_SYSTEM_PROMPT_PLANNING="You are a planning assistant focused on creating detailed analysis plans..."
export OLLAMA_SYSTEM_PROMPT_EXECUTION="You are a reverse engineering assistant specialized in analyzing binary code..."
```

## Performance Considerations

1. Using different models may increase latency due to model switching
2. Larger models typically provide better reasoning but are slower
3. For time-sensitive tasks, consider using smaller models for all phases
4. The planning and review phases generally benefit most from larger models

## Troubleshooting

If you encounter issues with model switching:

1. Verify that Ollama has the specified models installed
2. Check that the models are compatible with your system's resources
3. Ensure your Ollama server is running and accessible
4. Verify that the model names are spelled correctly

Use the `--list-models` flag to see what models are available on your Ollama server. 