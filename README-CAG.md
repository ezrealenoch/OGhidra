# Cache-Augmented Generation (CAG) for OGhidra

This document explains the Cache-Augmented Generation (CAG) feature in OGhidra, how it works, and how to configure it.

## What is Cache-Augmented Generation?

Cache-Augmented Generation (CAG) is an approach that enhances large language models by providing them with persistent, cached knowledge and contextual memory without needing real-time retrieval during inference.

Unlike traditional Retrieval-Augmented Generation (RAG), which requires vector databases and real-time embedding generation and retrieval, CAG pre-loads relevant knowledge and maintains session context to improve the quality of responses without the overhead of retrieval operations.

## Benefits in OGhidra

CAG provides several key benefits for binary analysis with OGhidra:

1. **Domain Knowledge**: Models have access to detailed information about Ghidra commands, their parameters, and best practices for binary analysis.

2. **Workflow Memory**: The system remembers previously decompiled functions, renamed entities, and analysis results within a session.

3. **Conversational Memory**: The model maintains context from previous exchanges in the conversation, allowing for more coherent multi-turn interactions.

4. **No Embedding Models Required**: Unlike RAG, no embedding models or vector stores are needed, making deployment simpler.

5. **Reduced Hallucinations**: By providing accurate reference material, the model is less likely to hallucinate capabilities or command parameters.

## Architecture

The CAG implementation consists of two main components:

### 1. Knowledge Cache

A persistent repository of domain-specific knowledge about:
- Function signatures and their parameters
- Common binary patterns
- Analysis workflows and techniques
- Heuristic analysis rules

This knowledge is pre-loaded and doesn't change during a session unless explicitly updated.

### 2. Session Cache

A dynamic cache that maintains information gathered during the current analysis session:
- Decompiled functions with their code
- Function and variable renames performed
- Previous analysis results
- Conversation history

This enables the model to reference work done earlier in the session.

## Configuration

You can configure CAG in your `.env` file with the following settings:

```
# Cache-Augmented Generation (CAG) Configuration
CAG_ENABLED=true                    # Enable or disable CAG feature
CAG_KNOWLEDGE_CACHE_ENABLED=true    # Enable domain knowledge cache
CAG_SESSION_CACHE_ENABLED=true      # Enable session memory cache
CAG_TOKEN_LIMIT=2000                # Maximum tokens to allocate for CAG context
```

### Command Line Options

You can also disable CAG at runtime with:

```
python main.py --interactive --disable-cag
```

## Interactive Commands

In interactive mode, you can check the status of the CAG system by typing:

```
cag
```

This will display information about the loaded knowledge cache and current session cache.

## How It Enhances Prompts

When CAG is enabled, the system enhances prompts in several ways:

1. **Knowledge Insertion**: Relevant domain knowledge is added to the prompt based on the user's query.

2. **Context History**: Recent conversation history is included to maintain continuity.

3. **Function Context**: Previously decompiled functions that are relevant to the current query are included.

4. **Analysis Results**: Previous analysis results that are semantically similar to the current query are included.

All of this is done while respecting token limits, with the most relevant information prioritized.

## Example Use Cases

### Function Renaming

When renaming a function, CAG provides:
- Information about the rename_function command and its parameters
- A workflow for how to properly rename functions in Ghidra
- Context about previously renamed functions in the session

### Binary Pattern Recognition

When analyzing unknown code, CAG provides:
- Known binary patterns that might match the code being analyzed
- Heuristics for identifying common algorithms or structures
- Context from previously analyzed similar functions

### Multi-step Analysis

For complex analysis tasks that span multiple queries, CAG maintains:
- The context of what has already been analyzed
- Functions that have already been decompiled
- Results from previous steps in the analysis

## Extending the Knowledge Base

You can extend the knowledge base by adding entries to the following files:

- `src/cag/knowledge/function_signatures.json`: Information about Ghidra functions
- `src/cag/knowledge/common_workflows.json`: Common workflows for binary analysis tasks
- `src/cag/knowledge/binary_patterns.json`: Patterns for recognizing common code structures
- `src/cag/knowledge/analysis_rules.json`: Heuristic rules for binary analysis

## Technical Details

The CAG system is implemented in the `src/cag` directory, with the following components:

- `knowledge_cache.py`: Manages the domain knowledge cache
- `session_cache.py`: Manages the session-specific cache
- `manager.py`: Coordinates knowledge and session caches, integrates with the Bridge

Session data is stored in the `ghidra_session_cache` directory, and knowledge data in the `ghidra_knowledge_cache` directory. 