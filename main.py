#!/usr/bin/env python3
"""
Main entry point for the Ollama-GhidraMCP Bridge application.
"""

import os
import sys
import argparse
import json
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Import after loading environment variables
from src.config import BridgeConfig
from src.bridge import Bridge
from src.ollama_client import OllamaClient
from src.ghidra_client import GhidraMCPClient

def print_header():
    """Print the application header."""
    width = 70
    header = [
        "OGhidra - Simplified Three-Phase Architecture",
        "------------------------------------------",
        "",
        "1. Planning Phase: Create a plan for addressing the query",
        "2. Tool Calling Phase: Execute tools to gather information",
        "3. Analysis Phase: Analyze results and provide answers",
        "",
        "For more information, see README-ARCHITECTURE.md"
    ]
    
    print('╔' + '═' * (width - 2) + '╗')
    for line in header:
        padding = (width - 2 - len(line))
        left_padding = padding // 2
        right_padding = padding - left_padding
        print('║' + ' ' * left_padding + line + ' ' * right_padding + '║')
    print('╚' + '═' * (width - 2) + '╝')

def run_interactive_mode(bridge: Bridge, config: BridgeConfig):
    """Run the bridge in interactive mode."""
    print("Ollama-GhidraMCP Bridge (Interactive Mode)")
    print(f"Default model: {bridge.ollama.config.model if hasattr(bridge, 'ollama') and hasattr(bridge.ollama, 'config') else config.ollama.model}") 
    
    # Initialize a list to store outputs from the current session for review
    current_session_log = []

    while True:
        try:
            user_input = input("Query (or 'exit', 'help', 'health', 'tools', 'models', 'vector-store', 'review_session', 'cag', 'analyze-function'): ") # Added cag, analyze-function
            if not user_input:
                continue

            if user_input.lower() in ('exit', 'quit'): # Allow 'quit' as well
                break
            elif user_input.lower() == 'health':
                # Check Ollama and GhidraMCP health
                # Corrected: Use bridge.ollama and bridge.ghidra
                ollama_health = bridge.ollama.check_health() if hasattr(bridge, 'ollama') else False
                ghidra_health = bridge.ghidra.check_health() if hasattr(bridge, 'ghidra') else False
                
                print("\n=== Health Check ===")
                print(f"Ollama API: {'OK' if ollama_health else 'NOT OK'}")
                print(f"GhidraMCP API: {'OK' if ghidra_health else 'NOT OK'}")
                print("====================\n")
                
                # Display vector store information if CAG is enabled
                if bridge.enable_cag and bridge.cag_manager:
                    print("\n=== Vector Store Information ===")
                    # Get vector store info from bridge
                    try:
                        vector_store_enabled = config.session_history.use_vector_embeddings if hasattr(config, 'session_history') else False
                        print(f"Vector embeddings: {'Enabled ✅' if vector_store_enabled else 'Disabled ❌'}")
                        
                        if vector_store_enabled and hasattr(bridge, 'memory_manager') and bridge.memory_manager is not None:
                            mm = bridge.memory_manager
                            if mm.vector_store:
                                vector_count = mm.vector_store.vectors.shape[0] if (hasattr(mm.vector_store, 'vectors') and 
                                                                               mm.vector_store.vectors is not None) else 0
                                print(f"Vectors available: {'Yes ✅' if vector_count > 0 else 'No ❌'}")
                                print(f"Vector count: {vector_count}")
                                
                                if vector_count > 0:
                                    print(f"Vector dimension: {mm.vector_store.vectors.shape[1]}")
                                    # Calculate mean norm
                                    import numpy as np
                                    norms = np.linalg.norm(mm.vector_store.vectors, axis=1)
                                    print(f"Mean vector norm: {float(np.mean(norms)):.4f}")
                                    
                                    # Show session IDs if available
                                    if hasattr(mm.vector_store, 'get_session_ids'):
                                        session_ids = mm.vector_store.get_session_ids()
                                        if session_ids:
                                            print(f"\nStored Session IDs ({len(session_ids)}):")
                                            for i, sid in enumerate(session_ids[:5]):  # Show first 5
                                                print(f"  {i+1}. {sid}")
                                            if len(session_ids) > 5:
                                                print(f"  ... and {len(session_ids) - 5} more")
                    except Exception as e:
                        print(f"Error displaying vector store info: {e}")
                    
                    print("===============================\n")
                continue
            elif user_input.lower() == 'vector-store':
                # Add dedicated command for vector store inspection
                print("\n=== Vector Store Information ===")
                # Get vector store info from bridge
                try:
                    vector_store_enabled = config.session_history.use_vector_embeddings if hasattr(config, 'session_history') else False
                    print(f"Vector embeddings: {'Enabled ✅' if vector_store_enabled else 'Disabled ❌'}")
                    
                    if vector_store_enabled and hasattr(bridge, 'memory_manager') and bridge.memory_manager is not None:
                        mm = bridge.memory_manager
                        if mm.vector_store:
                            vector_count = mm.vector_store.vectors.shape[0] if (hasattr(mm.vector_store, 'vectors') and 
                                                                           mm.vector_store.vectors is not None) else 0
                            print(f"Vectors available: {'Yes ✅' if vector_count > 0 else 'No ❌'}")
                            print(f"Vector count: {vector_count}")
                            
                            if vector_count > 0:
                                print(f"Vector dimension: {mm.vector_store.vectors.shape[1]}")
                                # Calculate mean norm
                                import numpy as np
                                norms = np.linalg.norm(mm.vector_store.vectors, axis=1)
                                print(f"Mean vector norm: {float(np.mean(norms)):.4f}")
                                
                                # Show session IDs if available
                                if hasattr(mm.vector_store, 'get_session_ids'):
                                    session_ids = mm.vector_store.get_session_ids()
                                    if session_ids:
                                        print(f"\nStored Session IDs ({len(session_ids)}):")
                                        for i, sid in enumerate(session_ids):
                                            print(f"  {i+1}. {sid}")
                except Exception as e:
                    print(f"Error displaying vector store info: {e}")
                
                print("===============================\n")
                continue
            elif user_input.lower() == 'models':
                # List available models
                # Corrected: Use bridge.ollama
                models = bridge.ollama.list_models() if hasattr(bridge, 'ollama') else []
                
                print("\n=== Available Models ===")
                for model in models:
                    print(f"- {model}")
                print("========================\n")
                continue
            elif user_input.lower() == 'tools':
                # Display all available Ghidra tools and their parameters
                print("\n=== Available Ghidra Tools ===")
                
                try:
                    # Corrected: Use bridge.ghidra
                    client = bridge.ghidra if hasattr(bridge, 'ghidra') else GhidraMCPClient(config.ghidra) # Fallback if bridge.ghidra not init
                    
                    # Get all public methods (excluding those starting with _ and known non-tools)
                    non_tool_methods = ['check_health', 'get_config', 'is_mock_mode', 'base_url', 'timeout', 'api_path', 'extended_url']
                    tools = [name for name in dir(client) if not name.startswith('_') and callable(getattr(client, name)) and name not in non_tool_methods]
                    
                    print(f"Found {len(tools)} available tools (via run-tool command):\n")
                    
                    for tool_name in sorted(tools):
                        tool_func = getattr(client, tool_name)
                        import inspect
                        signature = inspect.signature(tool_func)
                        params_desc = []
                        for param_name, param in signature.parameters.items():
                            if param_name == 'self': continue
                            if param.default is inspect.Parameter.empty:
                                params_desc.append(f"{param_name} (required)")
                            else:
                                default_val_str = f"\'{param.default}\'" if isinstance(param.default, str) else str(param.default)
                                params_desc.append(f"{param_name}={default_val_str}")
                        
                        doc = tool_func.__doc__.strip().split('\n')[0] if tool_func.__doc__ else "No description available"
                        print(f"  {tool_name}({', '.join(params_desc)})")
                        print(f"    {doc}")
                        print()
                except Exception as e:
                    print(f"Error loading tools: {str(e)}")
                print("===========================\n")
                continue
            elif user_input.lower() == 'cag': # Restored CAG command
                if bridge.enable_cag and bridge.cag_manager:
                    info = bridge.cag_manager.get_debug_info()
                    print("\n=== CAG Status ===")
                    print(f"CAG Enabled: {info['enabled']}")
                    print(f"Knowledge Cache Enabled: {info['knowledge_cache_enabled']}")
                    print(f"Session Cache Enabled: {info['session_cache_enabled']}")
                    print(f"Token Limit: {info['token_limit']}")
                    print("=================\n")
                else:
                    print("\nCAG is disabled. Enable it with CAG_ENABLED=true in your .env file.\n")
                continue
            elif user_input.lower() == 'help': # Restored help command
                print("\n=== Available Commands ===")
                print("exit, quit                            - Exit the application")
                print("health                                - Check API health and vector store status")
                print("vector-store                          - Display detailed vector store information")
                print("models                                - List available Ollama models")
                print("tools                                 - List all available Ghidra tools with parameters")
                print("run-tool tool_name(p1='v1', p2='v2')  - Execute a specific Ghidra tool directly")
                print("analyze-function [address]            - Analyze current function or specified address (shortcut)")
                print("review_session                        - Ask a query about the current session's interactions")
                print("clear_log                             - Clear the in-memory log for the current session review")
                print("cag                                   - Display Context-Aware Generation status")
                print("help                                  - Display this help message")
                print("Any other input will be treated as a query to the AI agent.")
                print("=========================\n")
                continue
            elif user_input.lower().startswith('run-tool '):
                # Execute a specific tool directly
                tool_str = user_input[9:].strip()  # Remove 'run-tool ' prefix
                
                TOOLS_WITH_AI_ANALYSIS = [
                    "analyze_function", 
                    "decompile_function", "decompile_function_by_address",
                    "list_functions", 
                    "list_imports", 
                    "list_exports", 
                    "list_strings"
                ]

                try:
                    if '(' not in tool_str or ')' not in tool_str:
                        print("\nInvalid format. Use: run-tool tool_name(param1='value1', param2='value2')\n")
                        continue
                        
                    tool_name = tool_str[:tool_str.find('(')].strip()
                    raw_params_str = tool_str[tool_str.find('(')+1:tool_str.rfind(')')].strip()
                    
                    params = {}
                    if raw_params_str:
                        # Improved parameter parsing to handle various types and quotes robustly
                        param_pairs = []
                        buffer = ""
                        in_quotes = False
                        quote_char = ''
                        paren_level = 0
                        for char in raw_params_str:
                            if char == ',' and not in_quotes and paren_level == 0:
                                param_pairs.append(buffer)
                                buffer = ""
                                continue
                            buffer += char
                            if char in ('"', "'"):
                                if not in_quotes:
                                    in_quotes = True
                                    quote_char = char
                                elif char == quote_char: # Closing quote
                                    # Check if this quote is escaped
                                    if buffer.endswith(f'\\\\{quote_char}'): # Check for escaped quote like \\" or \\'
                                        pass # It's an escaped quote, part of the string
                                    else:
                                        in_quotes = False
                                        quote_char = ''
                            elif char == '(' and not in_quotes:
                                paren_level +=1
                            elif char == ')' and not in_quotes:
                                paren_level -=1
                        param_pairs.append(buffer) # Add the last parameter

                        for pair in param_pairs:
                            if '=' in pair:
                                key, value_str_full = pair.split('=', 1)
                                key = key.strip()
                                value_str_from_pair = value_str_full.strip()
                                
                                if (value_str_from_pair.startswith("'") and value_str_from_pair.endswith("'")) or \
                                   (value_str_from_pair.startswith('"') and value_str_from_pair.endswith('"')):
                                    final_value_for_param = value_str_from_pair[1:-1].encode('utf-8').decode('unicode_escape') # Handle escapes
                                else: # Try to infer type for unquoted values
                                    if value_str_from_pair.lower() == "true": final_value_for_param = True
                                    elif value_str_from_pair.lower() == "false": final_value_for_param = False
                                    elif value_str_from_pair.lower() == "none": final_value_for_param = None
                                    elif value_str_from_pair.isdigit(): # Positive integers
                                        final_value_for_param = int(value_str_from_pair)
                                    elif value_str_from_pair.startswith('-') and value_str_from_pair[1:].isdigit(): # Negative integers
                                        final_value_for_param = int(value_str_from_pair)
                                    else: # Default to string if no other type matches
                                        try: # Check for float
                                            final_value_for_param = float(value_str_from_pair)
                                        except ValueError:
                                            final_value_for_param = value_str_from_pair # Fallback to string
                                params[key] = final_value_for_param
                    
                    # Corrected: Use bridge.ghidra
                    if hasattr(bridge.ghidra, tool_name):
                        tool_method = getattr(bridge.ghidra, tool_name)
                        
                        params_for_log = ', '.join([f'{k}={repr(v)}' for k, v in params.items()])
                        bridge.logger.info(f"Executing direct tool call via 'run-tool': {tool_name} with params: {params}")
                        raw_tool_result = tool_method(**params)

                        if tool_name in TOOLS_WITH_AI_ANALYSIS:
                            is_error = isinstance(raw_tool_result, str) and raw_tool_result.lower().startswith("error:")
                            
                            if not is_error:
                                formatted_tool_data = ""
                                if isinstance(raw_tool_result, dict) or isinstance(raw_tool_result, list):
                                    try:
                                        formatted_tool_data = json.dumps(raw_tool_result, indent=2)
                                    except TypeError: # Handle non-serializable data
                                        formatted_tool_data = str(raw_tool_result)
                                else:
                                    formatted_tool_data = str(raw_tool_result)
                            
                                print(f"\n=== Raw Output from {tool_name} (to be sent to AI) ===")
                                print(formatted_tool_data)
                                print("===========================================================")
                                current_session_log.append(f"=== Raw Output from {tool_name}({params_for_log}) ===\\n{formatted_tool_data}\\n")

                                analysis_prompt = None
                                if tool_name == "analyze_function":
                                    analysis_prompt = (
                                        f"The Ghidra tool '{tool_name}' was executed (parameters: {params_for_log}). "
                                        f"Its output is below. Based *only* on this provided data:\\n"
                                        f"1. Identify the primary function being analyzed (name and address).\\n"
                                        f"2. Summarize its apparent purpose or main actions based on decompiled code snippets and called functions.\\n"
                                        f"3. List any notable cross-references (calls to other functions, or data references) mentioned in the output.\\n"
                                        f"4. Point out any immediate observations a reverse engineer might find interesting (e.g., unusual patterns, specific API calls, complex logic, potential vulnerabilities like buffer overflows, format string bugs, etc.).\\n"
                                        f"Tool Output:\\n```json\\n{formatted_tool_data}\\n```"
                                    )
                                elif tool_name in ["decompile_function", "decompile_function_by_address"]:
                                    func_id = params.get('name', params.get('address', 'unknown function'))
                                    analysis_prompt = (
                                        f"The Ghidra tool '{tool_name}' was executed for function '{func_id}'. Its output (decompiled C code) is below. "
                                        f"Based *only* on this provided code:\\n"
                                        f"1. Provide a concise summary of the function's apparent purpose in one or two sentences.\\n"
                                        f"2. List any parameters and the inferred return type if visible.\\n"
                                        f"3. Identify any notable loops, conditional statements, or complex logic.\\n"
                                        f"4. Are there any calls to other functions or standard library functions? If so, list a few key ones and their likely purpose in this context.\\n"
                                        f"5. Are there any obvious security concerns (e.g., use of unsafe functions like strcpy, potential buffer overflows, format string vulnerabilities, hardcoded secrets)?\\n"
                                        f"Tool Output:\\n```c\\n{formatted_tool_data}\\n```"
                                    )
                                elif tool_name == "list_functions":
                                    analysis_prompt = (
                                        f"The Ghidra tool '{tool_name}' was executed. Its output (a list of functions) is below. "
                                        f"Based *only* on this provided data:\\n"
                                        f"1. How many functions are listed in this segment of the output?\\n"
                                        f"2. Are there any common prefixes or naming patterns observed in the function names (e.g., FUN_, LAB_, sub_, user_defined_)?\\n"
                                        f"3. List 5-10 function names that seem particularly interesting or suggestive of the program's core functionality (e.g., 'encrypt_data', 'network_send', 'parse_input', 'main').\\n"
                                        f"4. Are there any functions that suggest error handling or utility routines?\\n"
                                        f"Tool Output:\\n```json\\n{formatted_tool_data}\\n```"
                                    )
                                elif tool_name == "list_imports":
                                    analysis_prompt = (
                                        f"The Ghidra tool '{tool_name}' was executed. Its output (a list of imported functions/symbols and their source libraries) is below. "
                                        f"Based *only* on this provided data:\\n"
                                        f"1. What are the top 3-5 DLLs (libraries) from which functions are most frequently imported, if discernible? List them.\\n"
                                        f"2. For each of these top DLLs, list 2-3 example functions imported from it.\\n"
                                        f"3. Based on the imported functions, what are some general capabilities this program likely possesses (e.g., file I/O, network communication, cryptography, UI interaction, registry access)?\\n"
                                        f"4. Are there any specific imported functions that might be particularly interesting or suspicious from a security or reverse engineering perspective (e.g., related to encryption, process injection, anti-debugging, networking)? List a few and briefly state why.\\n"
                                        f"Tool Output:\\n```json\\n{formatted_tool_data}\\n```"
                                    )
                                elif tool_name == "list_exports":
                                    analysis_prompt = (
                                        f"The Ghidra tool '{tool_name}' was executed. Its output (a list of exported functions/symbols) is below. "
                                        f"This indicates functions that the binary makes available for other modules to call. Based *only* on this provided data:\\n"
                                        f"1. How many functions/symbols are exported in this segment of the output?\\n"
                                        f"2. List 3-5 exported names that seem most significant or indicative of the library's/program's primary purpose.\\n"
                                        f"3. Do any of the export names suggest this is a library (DLL/SO) providing an API, or an executable with specific entry points?\\n"
                                        f"4. Are there any names that look like standard C/C++ mangled names, or are they mostly human-readable?\\n"
                                        f"Tool Output:\\n```json\\n{formatted_tool_data}\\n```"
                                    )
                                elif tool_name == "list_strings":
                                    analysis_prompt = f"""The Ghidra tool '{tool_name}' was executed. Its output (a list of strings found in the binary) is below. 
Based *only* on this provided data:
1. Are there any strings in this segment of output that look like file paths, URLs, or IP addresses?
2. Are there any error messages or debug messages shown?
3. Are there any strings shown that suggest user interface elements (e.g., button labels, menu items)?
4. Do any strings shown hint at specific functionalities (e.g., "Enter password", "Encryption key", "Connecting to server...")?
5. Are there any unusual or obfuscated-looking strings in this segment?
6. Most importantly, are there any malicious or suspicious strings?
7. What can we infer about the behavior of the binary based on the strings?
Tool Output:
```json
{formatted_tool_data}
```"""
                                
                                if analysis_prompt:
                                    print(f"Sending output from {tool_name} to AI for analysis...")
                                    try:
                                        ai_analysis = bridge.ollama.generate(prompt=analysis_prompt)
                                        
                                        bridge.logger.info(f"AI analysis received snippet: '{ai_analysis[:50]}...'")
                                        print(f"DEBUG: AI Response Type: {type(ai_analysis)}, Is None: {ai_analysis is None}, Is Empty Str: {ai_analysis == ''}, Length: {len(ai_analysis) if ai_analysis else 0}")

                                        if ai_analysis and ai_analysis.strip():
                                            print("\n=== AI Analysis of Function Output ===")
                                            print(ai_analysis)
                                            print("=====================================")
                                            current_session_log.append(f"=== AI Analysis of {tool_name}({params_for_log}) ===\\n{ai_analysis}\\n")
                                        else:
                                            print("\nAI analysis returned empty or whitespace-only response.")
                                            current_session_log.append(f"=== AI Analysis of {tool_name}({params_for_log}) returned empty. ===\\n")

                                    except Exception as e:
                                        print(f"Error during AI analysis: {e}")
                                        bridge.logger.error(f"Error during AI analysis for {tool_name}: {e}", exc_info=True)
                                        current_session_log.append(f"=== Error during AI analysis of {tool_name}({params_for_log}): {e} ===\\n")
                                else:
                                    print(f"No specific AI analysis prompt configured for tool: {tool_name}. Raw output printed above.")
                            else: # Error in raw_tool_result
                                print(f"Error from tool {tool_name}: {raw_tool_result}")
                                current_session_log.append(f"=== Error from tool {tool_name}({params_for_log}): {raw_tool_result} ===\\n")
                        else: # Tool not in TOOLS_WITH_AI_ANALYSIS or tool execution error already handled
                             print(f"\nResult of {tool_name}({raw_params_str}):\\n{raw_tool_result}\\n") # Print raw result if no AI analysis
                             current_session_log.append(f"=== Result of {tool_name}({params_for_log}) ===\\n{raw_tool_result}\\n")
                    else:
                        print(f"\nUnknown tool: {tool_name}. Type 'tools' for a list of available tools.\\n")
                        
                except Exception as e:
                    print(f"Error executing tool: {e}")
                    bridge.logger.error(f"Error executing tool '{tool_str}': {e}", exc_info=True)
                    current_session_log.append(f"=== Error executing tool command '{tool_str}': {e} ===\\n")
            
            elif user_input.lower().startswith('analyze-function'): # Restored analyze-function shortcut
                try:
                    address = None
                    if user_input.lower().startswith('analyze-function '):
                        address_part = user_input[len('analyze-function '):].strip()
                        if address_part: # Ensure address_part is not empty
                            address = address_part
                    
                    print(f"\nExecuting: analyze_function({f'address=\"{address}\"' if address else ''})")
                    # Ensure bridge.ghidra is used
                    result = bridge.ghidra.analyze_function(address=address) if hasattr(bridge, 'ghidra') else "Ghidra client not available."
                    
                    print("\n============================================================")
                    print(f"Results from analyze_function:")
                    print("============================================================")
                    # Log result before printing, in case it's very long
                    log_entry_params = f"address={repr(address)}" if address else ""
                    current_session_log.append(f"=== Result of analyze-function({log_entry_params}) ===\\n{result}\\n")
                    print(result)
                    print("============================================================\n")
                except Exception as e:
                    print(f"Error analyzing function: {str(e)}")
                    bridge.logger.error(f"Error in 'analyze-function' shortcut: {e}", exc_info=True)
                    current_session_log.append(f"=== Error in analyze-function shortcut: {e} ===\\n")
                continue

            elif user_input.lower() == 'review_session':
                if not current_session_log:
                    print("\nNo interactions yet in this session to review.")
                    continue

                review_query = input("What would you like to ask about the work done in this session? (Type 'cancel' to abort): ")
                if not review_query or review_query.lower() == 'cancel':
                    print("Session review cancelled.")
                    continue

                print("\nCompiling session log for review...")
                session_context_str = "\n\n".join(current_session_log)
                
                review_prompt = (
                    f"You are an AI assistant. The user has been interacting with Ghidra tools in the current session. "
                    f"Below is a chronological log of the raw tool outputs and any subsequent AI analyses performed on those outputs. "
                    f"Please carefully review this entire session context to answer the user's question about the session.\\n\\n"
                    f"=============== BEGIN SESSION CONTEXT ===============\\n"
                    f"{session_context_str}\\n"
                    f"================ END SESSION CONTEXT ================\\n\\n"
                    f"USER'S QUESTION ABOUT THIS SESSION:\\n{review_query}\\n\\n"
                    f"Based on the provided session context, please provide a comprehensive answer to the user's question:"
                )

                print("Sending session context and query to AI for review...")
                try:
                    # Ensure bridge.ollama is used
                    ai_review_response = bridge.ollama.generate(prompt=review_prompt) if hasattr(bridge, 'ollama') else "Ollama client not available."
                    if ai_review_response and ai_review_response.strip() and ai_review_response != "Ollama client not available.":
                        print("\n=== AI Review of Session ===")
                        print(ai_review_response)
                        print("============================")
                    elif ai_review_response == "Ollama client not available.":
                         print(f"\n{ai_review_response}")
                    else:
                        print("\nAI review returned an empty or whitespace-only response.")
                except Exception as e:
                    print(f"Error during AI session review: {e}")
                    bridge.logger.error(f"Error during AI session review: {e}", exc_info=True)

            elif user_input.lower() == 'clear_log': 
                current_session_log.clear()
                print("Current session log cleared.")
            
            else:
                # Default to sending the query to the bridge for a general response
                # Ensure bridge.process_query is used
                try:
                    if hasattr(bridge, 'process_query'):
                        print("\nProcessing query with AI agent...")
                        result = bridge.process_query(user_input) # Assumes bridge has process_query
                        print("\n=== AI Agent Response ===")
                        print(result)
                        print("=========================\n")
                        current_session_log.append(f"=== AI Agent Response to Query: '{user_input}' ===\\n{result}\\n")
                    else:
                        print("\nBridge does not have process_query method. Cannot process general query.")
                        current_session_log.append(f"=== Attempted general query (not processed): '{user_input}' ===\\n")

                except Exception as e:
                    bridge.logger.error(f"Error processing query: {e}", exc_info=True)
                    print(f"\nError processing query: {type(e).__name__} - {e}\n")
                    current_session_log.append(f"=== Error processing query '{user_input}': {e} ===\\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        except Exception as e: # Catch-all for other unexpected errors in the loop
            print(f"An unexpected error occurred in the interactive loop: {e}")
            bridge.logger.error(f"Unexpected error in interactive loop: {e}", exc_info=True)
            # Optionally, decide if you want to break or continue
            # break 

def main():
    """Main entry point for the Ollama-GhidraMCP Bridge CLI."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Bridge between Ollama and GhidraMCP for binary analysis")
    parser.add_argument("--interactive", "-i", action="store_true", help="Enable interactive mode")
    parser.add_argument("--query", "-q", type=str, help="Single query to execute (non-interactive mode)")
    parser.add_argument("--include-capabilities", "-c", action="store_true", 
                       help="Include tool capabilities in the prompt (may use more tokens)")
    parser.add_argument("--disable-cag", action="store_true", 
                       help="Disable Cache-Augmented Generation (CAG)")
    
    args = parser.parse_args()
    
    # Check if we have a query or interactive mode
    if not args.interactive and not args.query:
        parser.print_help()
        return
    
    # Load configuration from environment
    config = BridgeConfig.from_env()
    
    # Override CAG settings from command line if specified
    if args.disable_cag:
        config.cag_enabled = False
    
    # Create the bridge
    bridge = Bridge(
        config=config, 
        include_capabilities=args.include_capabilities,
        max_agent_steps=config.max_steps,
        enable_cag=config.cag_enabled
    )
    
    # Print header
    print_header()
    
    if args.interactive:
        run_interactive_mode(bridge, config)
    else:
        # Single query mode
        result = bridge.process_query(args.query)
        print(result)

if __name__ == "__main__":
    sys.exit(main()) 