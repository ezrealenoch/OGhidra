# Command Normalization in OGhidra

This document explains the command normalization features implemented in OGhidra to improve compatibility with different AI models, especially those without native tool-calling support.

## Overview

AI models like Gemma that don't support Ollama's tool-calling API often struggle with the precise command formats needed for Ghidra interactions. The command normalization system automatically detects and corrects common formatting issues, allowing these models to work effectively with OGhidra.

## Key Features

### 1. Command Name Normalization

Automatically converts camelCase command names to snake_case when appropriate:

```
getCurrentFunction() → get_current_function()
decompileFunction() → decompile_function()
renameFunctionByAddress() → rename_function_by_address()
```

**Implementation details**:
- The system checks if the camelCase version doesn't exist but the snake_case version does
- Uses regex patterns to handle the conversion: 
  - First pattern: `(.)([A-Z][a-z]+)` → `\1_\2`
  - Second pattern: `([a-z0-9])([A-Z])` → `\1_\2`
- Logs the conversion for transparency

### 2. Parameter Name Standardization

Corrects common parameter naming inconsistencies:

```
function_address → address (in decompile_function_by_address, rename_function_by_address)
functionAddress → address (combines camelCase and parameter standardization)
```

**Common parameter mappings**:
- `rename_function_by_address`: Expects `address` and `new_name` parameters
- `decompile_function_by_address`: Expects `address` parameter
- `decompile_function`: Expects `name` parameter

### 3. Address Format Standardization

Handles various ways addresses might be formatted:

```
FUN_140001000 → 140001000 (removes FUN_ prefix)
0x140001000 → 140001000 (removes 0x prefix)
```

This is especially useful for functions like `rename_function_by_address` which require just the numerical address.

### 4. Alternative Command Format Detection

Recognizes various command formats that models might generate:

```
tool_execution command_name(params)
```
```json
{"tool": "command_name", "parameters": {"param": "value"}}
```
```
EXECUTE: command_name(params)  // correct format
```

The system logs when it detects and corrects an incorrect format.

### 5. Enhanced Error Messages

Provides clear, actionable error messages when issues occur:

- **Command name issues**: Suggests correct command names when a command isn't found
- **Parameter name issues**: Explains when parameter names are incorrect and suggests alternatives
- **Format issues**: Clarifies expected format vs. what was received
- **Recovery suggestions**: Offers recovery paths when possible

## Benefits

1. **Extended Model Compatibility**: Works with models that don't support tool-calling APIs
2. **Improved User Experience**: Reduces frustration from format-related errors
3. **Self-Healing Interactions**: Many common errors are automatically fixed
4. **Transparent Processing**: All corrections are logged to the terminal
5. **Consistent Interface**: Maintains standardized command interface across different models

## Example Terminal Output

When a command is normalized:

```
[INFO] Normalized command name from 'getCurrentFunction' to 'get_current_function'
[EXECUTING] get_current_function()
[RESULT] {'name': 'FUN_140001000', 'address': '140001000'}
```

When a parameter is standardized:

```
[INFO] Corrected parameter name from 'function_address' to 'address'
[EXECUTING] rename_function_by_address(address="140001000", new_name="initialize_data")
[RESULT] "Function at 140001000 renamed to initialize_data"
```

## Implementation Notes

The command normalization system is implemented in two main components:

1. `Bridge._normalize_command_name`: Handles command name normalization (camelCase → snake_case)
2. `CommandParser._validate_and_transform_params`: Handles parameter standardization and address format correction

These components work together to ensure that various command formats are properly interpreted and executed.

## Testing

The command normalization system is thoroughly tested in:

- `tests/test_command_normalization.py`: Unit tests for all normalization features
- `tests/test_bridge.py`: Integration tests within the Bridge class

## Best Practices

While the normalization system can correct many formatting issues, it's still best to:

1. Use the correct `EXECUTE:` prefix
2. Use snake_case for command names
3. Use the correct parameter names
4. Always quote string parameter values
5. Refer to function_signatures.json for the correct parameter names

## Future Improvements

Planned improvements for the command normalization system:

1. Expand parameter mapping to cover more edge cases
2. Add more detailed logging for debugging complex normalization scenarios
3. Implement rule-based correction for complex command patterns
4. Add automated feedback to help models learn the correct formats 