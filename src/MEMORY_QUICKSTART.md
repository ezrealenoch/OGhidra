# Memory System Quick Start Guide

This guide will help you quickly start using the memory features in Ollama-GhidraMCP Bridge.

## Initial Setup

1. **Create necessary directories:**
   ```bash
   mkdir -p data/vector_db
   ```

2. **Generate sample data:**
   ```bash
   # Generate 15 sample sessions
   python src/generate_sample_data.py --count 15 --enable-vector
   ```

3. **Check the memory system health:**
   ```bash
   python src/main.py --check-memory
   ```

## Basic Commands

### Display Memory Statistics
For a quick overview of memory usage:
```bash
python src/main.py --memory-stats
```

### Enable/Disable Vector Embeddings
Turn RAG capabilities on or off:
```bash
# Enable
python src/main.py --enable-vector-embeddings

# Disable
python src/main.py --disable-vector-embeddings
```

### Clear Memory
To reset all session history (use with caution!):
```bash
python src/main.py --clear-memory
```

## Interactive Mode

You can also access all memory features in interactive mode:

```bash
python src/main.py --interactive
```

Once in interactive mode, use these commands:
- `memory-health` - Run detailed memory system health check
- `memory-stats` - Display memory usage statistics
- `memory-clear` - Clear all session memory
- `memory-vectors-on` - Enable vector embeddings
- `memory-vectors-off` - Disable vector embeddings
- `help` - Show all available commands

## Run the Example

To see all memory features in action:
```bash
python src/memory_example.py
```

## Integration into Your Application

1. **Initialize the memory manager:**
   ```python
   from config import BridgeConfig
   from memory_manager import MemoryManager
   
   # Load configuration
   config = BridgeConfig()
   
   # Initialize memory manager
   memory_manager = MemoryManager(config)
   ```

2. **Track sessions and tool calls:**
   ```python
   # Start a session when a user begins a task
   session_id = memory_manager.start_session("User's task description")
   
   # Log each tool call as it happens
   memory_manager.log_tool_call(
       tool_name="tool_name",
       parameters={"param1": "value1"},
       status="success",
       result_preview="Brief description of result"
   )
   
   # End the session when the task is complete
   memory_manager.end_session(
       outcome="success",  # or "failure", "partial_success"
       reason="Reason for the outcome",
       generate_summary=True
   )
   ```

3. **Use RAG capabilities:**
   ```python
   # Find similar past sessions to assist with the current task
   similar_sessions = memory_manager.get_similar_sessions(
       query="User's current query or task",
       top_k=3
   )
   
   # Use the similar sessions to inform your response
   for session in similar_sessions:
       print(f"Similar task: {session['user_task']}")
       print(f"Summary: {session['summary']}")
   ```

## Tips for Best Results

1. **Store meaningful result previews** with each tool call to improve later retrieval and summarization
2. **Add proper outcome reasons** when ending sessions to help with understanding past work
3. **Enable vector embeddings** for similarity search capabilities
4. **Run health checks periodically** to ensure the memory system is operating correctly
5. **Consider cleaning old sessions** if performance degrades with a very large number of sessions

For more detailed documentation, see [README_MEMORY.md](README_MEMORY.md) 