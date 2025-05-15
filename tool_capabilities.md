# GhidraMCP Tool Capabilities

This document provides a comprehensive list of all available tools in the GhidraMCP API.

## Tool Overview

| Tool | Description | Parameters | Return Type | Test Status |
|------|-------------|------------|-------------|-------------|
| analyze_function | Analyze a function, including its decompiled code and all functions it calls. | address | str | ✅ Success |
| check_health | Check if the GhidraMCP server is reachable and responding. |  | bool | ✅ Success |
| decompile_function | Decompile a specific function by name and return the decompiled C code. | name | str | ✅ Success |
| decompile_function_by_address | Decompile a function at the given address. | address | str | ✅ Success |
| disassemble_function | Get assembly code (address: instruction; comment) for a function. | address | List[str] | ✅ Success |
| get_current_address | Get the address currently selected by the user. |  | str | ✅ Success |
| get_current_function | Get the function currently selected by the user. |  | str | ✅ Success |
| get_function_by_address | Get a function by its address. | address | str | ✅ Success |
| health_check | Check if the GhidraMCP server is available. |  | bool | ✅ Success |
| list_classes | List all namespace/class names in the program with pagination. | offset, limit | List[str] | ✅ Success |
| list_data_items | List defined data labels and their values with pagination. | offset, limit | List[str] | ✅ Success |
| list_exports | List exported functions/symbols with pagination. | offset, limit | List[str] | ✅ Success |
| list_functions | List all functions in the database. |  | List[str] | ✅ Success |
| list_imports | List imported symbols in the program with pagination. | offset, limit | List[str] | ✅ Success |
| list_methods | List all function names in the program with pagination. | offset, limit | List[str] | ✅ Success |
| list_namespaces | List all non-global namespaces in the program with pagination. | offset, limit | List[str] | ✅ Success |
| list_segments | List all memory segments in the program with pagination. | offset, limit | List[str] | ✅ Success |
| list_strings | List all strings in the program with pagination. | offset, limit | List[str] | ✅ Success |
| rename_data | Rename a data label at the specified address. | address, new_name | str | ✅ Success |
| rename_function | Rename a function by its current name to a new user-defined name. | old_name, new_name | str | ✅ Success |
| rename_function_by_address | Rename a function by its address. | function_address, new_name | str | ✅ Success |
| rename_variable | Rename a local variable within a function. | function_name, old_name, new_name | str | ✅ Success |
| search_functions_by_name | Search for functions whose name contains the given substring. | query, offset, limit | List[str] | ✅ Success |
| set_decompiler_comment | Set a comment for a given address in the function pseudocode. | address, comment | str | ✅ Success |
| set_disassembly_comment | Set a comment for a given address in the function disassembly. | address, comment | str | ✅ Success |
| set_function_prototype | Set a function's prototype. | function_address, prototype | str | ✅ Success |
| set_local_variable_type | Set a local variable's type. | function_address, variable_name, new_type | str | ✅ Success |

## Detailed Tool Documentation

### analyze_function

Analyze a function, including its decompiled code and all functions it calls.
If no address is provided, uses the current function.

Args:
    address: Function address (optional)
    
Returns:
    Comprehensive function analysis including decompiled code and referenced functions

**Signature:**
```python
analyze_function(address: str = None) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | No | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
=== ANALYSIS OF FUNCTION AT 004052b0 ===


/* Setting prototype: void test_function(int param1, char* param2) */

undefined4 func_004052b0_renamed_test(void)

{
  undefined4 in_stack_0000000c;
  
                    /* Test comment added by API test */
  thunk_FUN_0040fd90();
  LOCK();
  UNLOCK();
 ...
```

---

### check_health

Check if the GhidraMCP server is reachable and responding.

Returns:
    True if GhidraMCP is healthy, False otherwise

**Signature:**
```python
check_health() -> bool
```

**Parameters:**
No parameters.

**Test Results:**
- Status: ✅ Success
- Return Type: bool
- Sample Result:
```
True
```

---

### decompile_function

Decompile a specific function by name and return the decompiled C code.

Args:
    name: Function name
    
Returns:
    Decompiled C code

**Signature:**
```python
decompile_function(name: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| name | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
BOOL __stdcall CloseHandle_renamed_test_renamed_test_renamed_test(HANDLE hObject)

{
  BOOL BVar1;
  
                    /* WARNING: Could not recover jumptable at 0x00405190. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  BVar1 = CloseHandle(hObject...
```

---

### decompile_function_by_address

Decompile a function at the given address.

Args:
    address: Function address
    
Returns:
    Decompiled function

**Signature:**
```python
decompile_function_by_address(address: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```

/* Setting prototype: void test_function(int param1, char* param2) */

undefined4 func_004052b0_renamed_test(void)

{
  undefined4 in_stack_0000000c;
  
                    /* Test comment added by API test */
  thunk_FUN_0040fd90();
  LOCK();
  UNLOCK();
  return in_stack_0000000c;
}

```

---

### disassemble_function

Get assembly code (address: instruction; comment) for a function.

Args:
    address: Function address
    
Returns:
    Disassembled function

**Signature:**
```python
disassemble_function(address: str) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
004052b0: PUSH 0x4b6020 ; Test comment added by API test
004052b5: CALL 0x0040f72c 
004052ba: POP ECX 
004052bb: POP EDX 
004052bc: XCHG dword ptr [ESP],EAX 
... truncated ...
```

---

### get_current_address

Get the address currently selected by the user.

Returns:
    Current address

**Signature:**
```python
get_current_address() -> str
```

**Parameters:**
No parameters.

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
004a83bc
```

---

### get_current_function

Get the function currently selected by the user.

Returns:
    Current function

**Signature:**
```python
get_current_function() -> str
```

**Parameters:**
No parameters.

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Function: entry at 004a83bc
Signature: undefined __register entry(void)
```

---

### get_function_by_address

Get a function by its address.

Args:
    address: Function address
    
Returns:
    Function information

**Signature:**
```python
get_function_by_address(address: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Function: func_004052b0_renamed_test at 004052b0
Signature: undefined4 __register func_004052b0_renamed_test(void)
Entry: 004052b0
Body: 004052b0 - 004052bf
```

---

### health_check

Check if the GhidraMCP server is available.

Returns:
    True if the server is available, False otherwise

**Signature:**
```python
health_check() -> bool
```

**Parameters:**
No parameters.

**Test Results:**
- Status: ✅ Success
- Return Type: bool
- Sample Result:
```
True
```

---

### list_classes

List all namespace/class names in the program with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of class names

**Signature:**
```python
list_classes(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
ADVAPI32.DLL
COMCTL32.DLL
KERNEL32.DLL
OLEAUT32.DLL
USER32.DLL
... truncated ...
```

---

### list_data_items

List defined data labels and their values with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of data items

**Signature:**
```python
list_data_items(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
00400000: IMAGE_DOS_HEADER_00400000 = 
00400100: IMAGE_NT_HEADERS32_00400100 = 
004001f8: (unnamed) = 
00400220: (unnamed) = 
00400248: (unnamed) = 
... truncated ...
```

---

### list_exports

List exported functions/symbols with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of exported symbols

**Signature:**
```python
list_exports(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
Ordinal_2 -> 0040fc10
__dbk_fcall_wrapper -> 0040fc10
entry -> 004a83bc
dbkFCallWrapperAddr -> 004b063c
Ordinal_1 -> 004b063c
```

---

### list_functions

List all functions in the database.

Returns:
    List of functions

**Signature:**
```python
list_functions() -> List[str]
```

**Parameters:**
No parameters.

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
CloseHandle_renamed_test_renamed_test_renamed_test at 00405190
GetStdHandle at 00405198
WriteFile at 004051a0
FindClose at 004051a8
FindFirstFileW at 004051b0
... truncated ...
```

---

### list_imports

List imported symbols in the program with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of imported symbols

**Signature:**
```python
list_imports(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
GetACP -> EXTERNAL:00000001
GetExitCodeProcess -> EXTERNAL:00000002
CloseHandle -> EXTERNAL:00000003
LocalFree -> EXTERNAL:00000004
SizeofResource -> EXTERNAL:00000005
... truncated ...
```

---

### list_methods

List all function names in the program with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of function names

**Signature:**
```python
list_methods(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
CloseHandle_renamed_test_renamed_test_renamed_test
GetStdHandle
WriteFile
FindClose
FindFirstFileW
... truncated ...
```

---

### list_namespaces

List all non-global namespaces in the program with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of namespaces

**Signature:**
```python
list_namespaces(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
ADVAPI32.DLL
COMCTL32.DLL
KERNEL32.DLL
OLEAUT32.DLL
USER32.DLL
... truncated ...
```

---

### list_segments

List all memory segments in the program with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of memory segments

**Signature:**
```python
list_segments(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
Headers: 00400000 - 004003ff
.text: 00401000 - 004a67ff
.itext: 004a7000 - 004a8bff
.data: 004a9000 - 004ac9ff
.bss: 004ad000 - 004b4257
... truncated ...
```

---

### list_strings

List all strings in the program with pagination.

Args:
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of strings

**Signature:**
```python
list_strings(offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
0040106a: "ShortInt"
00401106: "Pointer"
00401192: "Single"
0040122e: "ByteBool"
004012e0: "\n\nAnsiString"
... truncated ...
```

---

### rename_data

Rename a data label at the specified address.

Args:
    address: Data address
    new_name: New data name
    
Returns:
    Result of the rename operation

**Signature:**
```python
rename_data(address: str, new_name: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | Yes | None | <class 'str'> |
| new_name | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Rename data attempted
```

---

### rename_function

Rename a function by its current name to a new user-defined name.

Args:
    old_name: Current function name
    new_name: New function name
    
Returns:
    Result of the rename operation

**Signature:**
```python
rename_function(old_name: str, new_name: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| old_name | Yes | None | <class 'str'> |
| new_name | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Renamed successfully
```

---

### rename_function_by_address

Rename a function by its address.

Args:
    function_address: Function address
    new_name: New name
    
Returns:
    Result of the rename operation

**Signature:**
```python
rename_function_by_address(function_address: str, new_name: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| function_address | Yes | None | <class 'str'> |
| new_name | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Function renamed successfully
```

---

### rename_variable

Rename a local variable within a function.

Args:
    function_name: Function name
    old_name: Current variable name
    new_name: New variable name
    
Returns:
    Result of the rename operation

**Signature:**
```python
rename_variable(function_name: str, old_name: str, new_name: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| function_name | Yes | None | <class 'str'> |
| old_name | Yes | None | <class 'str'> |
| new_name | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Function not found
```

---

### search_functions_by_name

Search for functions whose name contains the given substring.

Args:
    query: Search query
    offset: Offset to start from
    limit: Maximum number of results
    
Returns:
    List of matching functions

**Signature:**
```python
search_functions_by_name(query: str, offset: int = 0, limit: int = 100) -> List[str]
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| query | Yes | None | <class 'str'> |
| offset | No | 0 | <class 'int'> |
| limit | No | 100 | <class 'int'> |

**Test Results:**
- Status: ✅ Success
- Return Type: list
- Sample Result:
```
CloseHandle_renamed_test_renamed_test_renamed_test_renamed_test @ 00405190
```

---

### set_decompiler_comment

Set a comment for a given address in the function pseudocode.

Args:
    address: Address
    comment: Comment
    
Returns:
    Result of the operation

**Signature:**
```python
set_decompiler_comment(address: str, comment: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | Yes | None | <class 'str'> |
| comment | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Comment set successfully
```

---

### set_disassembly_comment

Set a comment for a given address in the function disassembly.

Args:
    address: Address
    comment: Comment
    
Returns:
    Result of the operation

**Signature:**
```python
set_disassembly_comment(address: str, comment: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| address | Yes | None | <class 'str'> |
| comment | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Comment set successfully
```

---

### set_function_prototype

Set a function's prototype.

Args:
    function_address: Function address
    prototype: Function prototype
    
Returns:
    Result of the operation

**Signature:**
```python
set_function_prototype(function_address: str, prototype: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| function_address | Yes | None | <class 'str'> |
| prototype | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Failed to set function prototype: Failed to set function prototype on Swing thread: null
```

---

### set_local_variable_type

Set a local variable's type.

Args:
    function_address: Function address
    variable_name: Variable name
    new_type: New type
    
Returns:
    Result of the operation

**Signature:**
```python
set_local_variable_type(function_address: str, variable_name: str, new_type: str) -> str
```

**Parameters:**
| Name | Required | Default | Type |
|------|----------|---------|------|
| function_address | Yes | None | <class 'str'> |
| variable_name | Yes | None | <class 'str'> |
| new_type | Yes | None | <class 'str'> |

**Test Results:**
- Status: ✅ Success
- Return Type: str
- Sample Result:
```
Setting variable type: local_10 to char* in function at 004052b0

Type not found directly: char*

Result: Failed to set variable type
```

---

## Calling Tools from AI Agent

When using these tools from the AI agent, use the following format:

```
EXECUTE: tool_name(param1="value1", param2="value2")
```

For example:

```
EXECUTE: decompile_function(name="main")
```

## Generated Documentation

This documentation was automatically generated by the ToolCapabilityTester on 2025-05-15 02:53:35.
