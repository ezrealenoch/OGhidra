# Enabled Ghidra MCP Tools

This document provides an overview of the currently enabled tools in the Ghidra MCP API.

## Core Analysis Tools

These are the most important tools for analyzing code in Ghidra:

### `analyze_function(address=None)`
Provides comprehensive analysis of a function, including its decompiled code and all functions it calls.
If no address is provided, automatically uses the currently selected function in Ghidra.

### `decompile_function(name)`
Decompiles a specific function by name and returns the C code.

### `decompile_function_by_address(address)`
Decompiles a function at the specified address.

### `disassemble_function(address)`
Returns assembly code (with address, instruction, and comments) for a function.

## Navigation & Information Tools

### `get_current_function()`
Returns the function currently selected by the user in Ghidra.

### `get_current_address()`
Returns the address currently selected by the user in Ghidra.

### `get_function_by_address(address)`
Gets information about a function at the specified address.

### `list_functions()`
Lists all functions in the database.

## Search & Discovery Tools

### `list_methods(offset=0, limit=100)`
Lists all function names in the program with pagination.

### `list_classes(offset=0, limit=100)`
Lists all namespace/class names in the program.

### `list_strings(offset=0, limit=100)`
Lists all strings in the program with pagination.

### `search_functions_by_name(query, offset=0, limit=100)`
Searches for functions whose name contains the given substring.

### `list_imports(offset=0, limit=100)`
Lists imported symbols in the program.

### `list_exports(offset=0, limit=100)`
Lists exported functions/symbols.

### `list_segments(offset=0, limit=100)`
Lists all memory segments in the program.

### `list_data_items(offset=0, limit=100)`
Lists defined data labels and their values.

### `list_namespaces(offset=0, limit=100)`
Lists all non-global namespaces in the program.

## Modification Tools

### `rename_function(old_name, new_name)`
Renames a function by its current name to a new user-defined name.

### `rename_function_by_address(function_address, new_name)`
Renames a function by its address.

### `rename_data(address, new_name)`
Renames a data label at the specified address.

## System Tools

### `health_check()`
Checks if the GhidraMCP server is available.

### `check_health()`
Checks if the GhidraMCP server is reachable and responding.

## Disabled Tools

The following tools have been disabled to focus on the most useful analysis functionality:

- `rename_variable`
- `safe_get`
- `safe_post`
- `set_decompiler_comment`
- `set_disassembly_comment`
- `set_function_prototype`
- `set_local_variable_type`

## Tool Usage

To use these tools from the AI agent, use the following format:

```
EXECUTE: tool_name(param1="value1", param2="value2")
```

For example:

```
EXECUTE: analyze_function()
EXECUTE: decompile_function(name="main")
EXECUTE: list_strings(limit=10)
``` 