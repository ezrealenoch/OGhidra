"""
ADK Agent workflow for analyzing Ghidra projects using a multi-agent loop.

This module defines a sequence of agents (Planner, Executor, Analyzer, Reviewer)
orchestrated by a LoopAgent to answer user queries about a Ghidra project
by interacting with the GhidraMCP server.
"""

import os
import json
import logging
import asyncio
import re  # <-- Add import for regular expressions
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool, exit_loop

# --- Configuration ---
load_dotenv() # Load .env file if present

# Setup logger (ensure logger is defined before use)
logger = logging.getLogger(__name__)
# Configure basic logging level if needed (optional, could be done elsewhere)
# logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Import Ghidra functions (to be wrapped)
try:
    # Import the actual Python functions defined in ghidra_mcp.py
    from src.adk_tools.ghidra_mcp import (
        ghidra_list_functions as _ghidra_list_functions,
        ghidra_decompile_function_by_name as _ghidra_decompile_function_by_name,
        ghidra_decompile_function_by_address as _ghidra_decompile_function_by_address,
        ghidra_rename_function_by_address as _ghidra_rename_function_by_address,
        ghidra_set_decompiler_comment as _ghidra_set_decompiler_comment,
        ghidra_set_disassembly_comment as _ghidra_set_disassembly_comment,
        ghidra_get_current_function as _ghidra_get_current_function,
        ghidra_get_current_address as _ghidra_get_current_address
    )

    # Wrap functions with FunctionTool for ADK
    ALL_GHIDRA_TOOLS = [
        FunctionTool(func=_ghidra_list_functions),
        FunctionTool(func=_ghidra_decompile_function_by_name),
        FunctionTool(func=_ghidra_decompile_function_by_address),
        FunctionTool(func=_ghidra_rename_function_by_address),
        FunctionTool(func=_ghidra_set_decompiler_comment),
        FunctionTool(func=_ghidra_set_disassembly_comment),
        FunctionTool(func=_ghidra_get_current_function),
        FunctionTool(func=_ghidra_get_current_address)
    ]
    # Extract just the names for the Planner agent's instructions
    AVAILABLE_TOOL_NAMES = [tool.name for tool in ALL_GHIDRA_TOOLS]
    logger.info(f"Successfully imported and wrapped Ghidra ADK tools: {AVAILABLE_TOOL_NAMES}")

except ImportError as e:
    # Use the logger here safely now
    logger.error(f"Failed to import Ghidra ADK functions: {e}. Ensure src/adk_tools/ghidra_mcp.py exists and defines the functions.")
    ALL_GHIDRA_TOOLS = []
    AVAILABLE_TOOL_NAMES = []

# Configure LiteLLM to use Ollama (adjust model as needed)
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", "cogito:32b")
# Ensure the model name includes the provider prefix for LiteLLM
if not OLLAMA_MODEL_NAME.startswith("ollama/") and not OLLAMA_MODEL_NAME.startswith("ollama_chat/"):
    # Default to ollama/ if no prefix found
    OLLAMA_MODEL_STRING = f"ollama/{OLLAMA_MODEL_NAME}"
    logger.warning(f"OLLAMA_MODEL env var ('{OLLAMA_MODEL_NAME}') did not include provider prefix. Using '{OLLAMA_MODEL_STRING}' for LiteLLM.")
else:
    OLLAMA_MODEL_STRING = OLLAMA_MODEL_NAME

if not os.getenv("OLLAMA_API_BASE"):
    os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"
    logger.info(f"OLLAMA_API_BASE not set, defaulting to {os.environ['OLLAMA_API_BASE']}")
else:
     logger.info(f"Using OLLAMA_API_BASE from environment: {os.environ['OLLAMA_API_BASE']}")

LLM_INSTANCE = LiteLlm(model=OLLAMA_MODEL_STRING)
logger.info(f"Using Ollama model via LiteLLM: {OLLAMA_MODEL_STRING}")

# --- Agent Definitions ---

# Helper to generate tool list string for prompts
def _format_tool_list_for_prompt(tools: List[FunctionTool]) -> str:
    lines = []
    for tool in tools:
        try:
            # Extract parameter info from type hints
            params_dict = tool.func.__annotations__.copy() # Use copy
            # Remove return type hint if present
            params_dict.pop('return', None)

            if not params_dict:
                # Explicitly state no arguments if params_dict is empty
                func_sig = f"{tool.name}() - Takes no arguments."
            else:
                # Format parameters clearly
                params_str = ", ".join([f"{k}: {v.__name__ if hasattr(v, '__name__') else v}" for k, v in params_dict.items()])
                func_sig = f"{tool.name}({params_str})"

            # Get the first line of the docstring
            docstring_first_line = tool.func.__doc__.strip().split('\n')[0] if tool.func.__doc__ else "No description available."
            lines.append(f"- `{func_sig}`: {docstring_first_line}")

        except Exception as e:
            logger.warning(f"Could not format tool {tool.name} for prompt: {e}")
            # Provide a fallback representation
            lines.append(f"- `{tool.name}`: (Error formatting description)")
    return "\n".join(lines)

# Modified planner instruction to avoid function calling issues with Ollama/LiteLLM
PLANNER_INSTRUCTION_ROBUST = f"""
You are the Planning Agent for a Ghidra analysis task.

**IMPORTANT FIRST STEP:** Check the 'user_query'. If the query is EXACTLY the text "EXIT LOOP", 
respond with: {{"exit_loop": true}}

If the query is NOT "EXIT LOOP", proceed with the following planning task:
Your goal is to analyze the user's query and the current state (including past tool results and analysis)
and create a step-by-step plan of Ghidra tool calls required to gather the necessary information.

Available Tools (Use EXACT names and provide ONLY the required parameters):
{_format_tool_list_for_prompt(ALL_GHIDRA_TOOLS)}

Input State Keys:
- user_query: The original request from the user.
- last_tool_result (optional): The result from the previous tool execution, including status ('success' or 'error') and result/message.
- current_analysis (optional): The analysis synthesized so far.
- ghidra_plan (optional): The existing plan (list of dictionaries), if refining.

**IMPORTANT**: 
- Your response MUST be in JSON format.
- For queries that are NOT "EXIT LOOP", output a JSON list of dictionaries, where each dictionary represents a single tool call.
- Each dictionary MUST have 'tool_name' and 'parameters' (a dictionary of arguments for that specific tool).
- If a tool takes no arguments, the 'parameters' dictionary MUST be empty: {{}}.
- If no tool calls are needed, output an empty list: [].

Example response for a standard query:
[
  {{"tool_name": "ghidra_list_functions", "parameters": {{}}}},
  {{"tool_name": "ghidra_decompile_function_by_name", "parameters": {{"function_name": "main"}}}}
]

Example response for "EXIT LOOP" query:
{{"exit_loop": true}}

DO NOT explain your reasoning or add any text before or after the JSON.
ONLY respond with the JSON array of tool calls or the exit_loop object.
"""

# 1. Planning Agent - Modified to work with LiteLLM and Ollama
planning_agent = LlmAgent(
    name="Planner",
    model=LLM_INSTANCE,
    instruction=PLANNER_INSTRUCTION_ROBUST,  # Use the robust instruction that doesn't rely on function calling
    output_key="ghidra_plan"  # Output the plan to this state key
)

# 2. Tool Execution Agent - Modified to handle the JSON directly
EXECUTOR_INSTRUCTION_NO_FUNCTION_CALLING = """
You are the Tool Execution Agent for a Ghidra analysis task.

CRITICAL INFORMATION: DO NOT USE FUNCTION CALLING IN YOUR RESPONSE. Only respond with plain JSON.

Follow these steps exactly:
1. Examine the 'ghidra_plan' state key, which contains a list of planned tool calls.
2. If the list is empty, respond with this exact JSON: {"status": "no_plan", "message": "No tool calls in plan."}
3. If the list contains an object with {"exit_loop": true}, note this in your response as: {"status": "exit", "message": "Exit loop requested"}
4. Otherwise, extract the first tool call from the list. Note the tool_name and parameters for manual execution.

For step 4, format your response as the following JSON:
{
  "action": "execute_tool",
  "tool_name": "[extracted tool name]",
  "parameters": [extracted parameters object],
  "remove_from_plan": true
}

Example response for a ghidra_list_functions tool call:
{"action":"execute_tool","tool_name":"ghidra_list_functions","parameters":{},"remove_from_plan":true}

DO NOT format this as a function call. Instead, provide a plain JSON object that the ADK system can parse to identify what tool to execute.
CRITICAL: DO NOT include any text, explanation, or markdown outside of the JSON.
"""

tool_executor_agent = LlmAgent(
    name="Executor",
    model=LLM_INSTANCE,
    instruction=EXECUTOR_INSTRUCTION_NO_FUNCTION_CALLING,
    include_contents='none',
    # Explicitly remove tools parameter to avoid function calling altogether
    # The handler function will process the JSON response and call the appropriate tool
)

# 3. Analysis Agent - Interprets the tool results
ANALYZER_INSTRUCTION_STRICT = """
You are the Analysis Agent for a Ghidra binary analysis task.

Your role is to analyze the outputs from Ghidra tools and provide insights about the binary.

IMPORTANT: Return only plain text analysis. DO NOT return JSON, function calls, or tool usage suggestions. 
Analyze what has been discovered, not what could be discovered.

Input state:
- user_query: The original user query.
- last_tool_result: The most recent tool execution result.
- current_analysis: The analysis synthesized so far, which you should build upon.
- ghidra_plan: The remaining plan items.

Guidelines:
1. Focus on the most recent tool result and its implications.
2. Highlight potential security vulnerabilities, code patterns, and function purposes.
3. Be specific about addresses, function names, and code structure.
4. Build upon prior analysis without excessive repetition.
5. If encountering errors from tools, indicate what might be missing or wrong and suggest refinements.
6. Use clear, concise language, prioritizing accuracy over verbosity.

Return ONLY textual analysis without any special formatting or JSON structures.
"""

analysis_agent = LlmAgent(
    name="Analyzer",
    model=LLM_INSTANCE,
    instruction=ANALYZER_INSTRUCTION_STRICT,
    output_key="current_analysis"
)

# 4. Review Agent - Evaluates progress and suggests next steps
REVIEWER_INSTRUCTION = """
You are the Review Agent for a Ghidra binary analysis task.

Your role is to evaluate the current state of the analysis and determine what to do next:
1. Continue with the existing plan if results are good and more steps remain.
2. Suggest refining or creating a new plan if we're encountering errors or got unexpected results.
3. Conclude and summarize when the user query has been sufficiently answered.
4. Explicitly request to exit the loop if the analysis seems impossible, tools are consistently failing (check 'last_tool_result'), or the query cannot be answered with the available Ghidra tools.

Input State:
- user_query: The original user question.
- current_analysis: Analysis generated by the Analysis Agent.
- ghidra_plan: The remaining planned tool calls.
- last_tool_result: The most recent tool execution result (check status: 'success' or 'error').

Provide your response as ONLY ONE of the following directives based on your evaluation:
- If more tool calls from the plan are needed: "CONTINUE: <brief explanation>"
- If the plan needs revision due to errors or unexpected results: "REVISE_PLAN: <explanation of what's needed>"
- If the analysis is complete and answers the query: "FINAL_ANSWER: <comprehensive summary answering the user query>"
- If the task should stop due to consistent errors or impossibility: "EXIT_LOOP: <reason, e.g., Consistent tool errors, Binary incompatible, Query unanswerable>"

Only provide the most appropriate single directive from the options above.
"""

review_agent = LlmAgent(
    name="Reviewer",
    model=LLM_INSTANCE,
    instruction=REVIEWER_INSTRUCTION,
)

# --- Main Loop Agent ---

# Define the loop agent using the sub-agents in sequence
agent = LoopAgent(
    name="ghidra_analyzer", # This name should match the directory/module name
    sub_agents=[
        planning_agent,
        tool_executor_agent,
        analysis_agent,
        review_agent
    ],
    max_iterations=10, # Limit the number of loops
    description="An agent that analyzes Ghidra projects by planning and executing Ghidra tool calls."
)

# --- Executor Agent Helper Functions ---

def handle_executor_response(callback_context=None, llm_response=None, event=None, state=None):
    """
    Process the ghidra_plan state directly, execute the appropriate tool,
    and update the state. Ignores the Executor LLM's response.
    This function is called by the after_model_callback of the Executor agent.

    Args:
        callback_context: The context provided by ADK (contains state and event)
        llm_response: The response from the LLM (IGNORED)
        event: Backward compatibility parameter (IGNORED)
        state: Backward compatibility parameter (preferred way to get state)
    """
    current_state = None
    tool_result = None
    logger.debug("Executor Handler: Bypassing LLM response, checking state['ghidra_plan'] directly.")

    # --- Safely extract state --- 
    try:
        if callback_context and hasattr(callback_context, 'state'):
            current_state = callback_context.state
        elif state:
            current_state = state
        
        if not current_state:
             logger.error("Executor Handler: Could not retrieve state.")
             if state: state['last_tool_result'] = {"status": "error", "message": "Internal error: State not found in handler."}
             return None # Must return None from callback

        # --- Process ghidra_plan from State --- 
        ghidra_plan = current_state.get('ghidra_plan', [])

        # Ensure ghidra_plan is a list (it might be a JSON string from Planner initially)
        if isinstance(ghidra_plan, str):
            try:
                ghidra_plan = json.loads(ghidra_plan)
                if not isinstance(ghidra_plan, list):
                     logger.warning(f"Executor Handler: Parsed ghidra_plan from string, but it's not a list: {type(ghidra_plan)}")
                     ghidra_plan = [] # Treat as invalid plan
                else:
                     logger.info("Executor Handler: Successfully parsed ghidra_plan from JSON string in state.")
                     # Update state with the parsed list
                     current_state['ghidra_plan'] = ghidra_plan 
            except json.JSONDecodeError:
                logger.error(f"Executor Handler: ghidra_plan in state was a string but failed to parse as JSON: '{ghidra_plan[:100]}...'")
                ghidra_plan = [] # Treat as invalid plan

        if not isinstance(ghidra_plan, list):
            logger.error(f"Executor Handler: ghidra_plan in state is not a list or valid JSON string. Type: {type(ghidra_plan)}. Value: {str(ghidra_plan)[:100]}...")
            tool_result = {"status": "error", "message": f"Internal error: Invalid ghidra_plan format in state ({type(ghidra_plan)})."}
            # ghidra_plan = [] # Resetting here might hide the error, let the check below handle empty list

        # --- Determine Action based on Plan --- 
        # Check if the plan (now guaranteed to be a list or reset if invalid) is empty
        if not ghidra_plan: 
            logger.info("Executor Handler: ghidra_plan is empty or invalid.")
            # If tool_result was already set due to invalid format, use that, otherwise set no_plan
            if tool_result is None:
                tool_result = {"status": "no_plan", "message": "No tool calls remaining in plan or plan was invalid."}
        else:
            # Get the first planned tool call
            next_tool_call = ghidra_plan[0]
            tool_name = None # Define tool_name here for broader scope
            if not isinstance(next_tool_call, dict):
                logger.error(f"Executor Handler: First item in ghidra_plan is not a dictionary: {next_tool_call}")
                tool_result = {"status": "error", "message": f"Internal error: Invalid item format in ghidra_plan."}
            else:
                tool_name = next_tool_call.get("tool_name")
                parameters = next_tool_call.get("parameters", {})

                if not tool_name:
                    tool_result = {"status": "error", "message": "Plan item missing 'tool_name'."}
                elif tool_name == "exit_loop": # Handle explicit exit request from Planner
                    tool_result = {"status": "exit", "message": "Exit loop requested by Planner."}
                    try:
                        from google.adk.tools import exit_loop as exit_loop_func
                        class MockContext:
                             def __getattr__(self, name): 
                                 return lambda *args, **kwargs: None 
                        exit_loop_func(callback_context if callback_context else MockContext())
                        logger.info("Executor Handler: Called exit_loop ADK function based on plan.")
                    except Exception as exit_e:
                        logger.warning(f"Executor Handler: Failed to call exit_loop ADK function: {exit_e}")
                else:
                    # Find and execute the actual tool
                    tool_func = None
                    for tool in ALL_GHIDRA_TOOLS:
                        if tool.name == tool_name:
                            tool_func = tool.func
                            break

                    if tool_func is None:
                        tool_result = {"status": "error", "message": f"Tool '{tool_name}' specified in plan not found.", "tool": tool_name}
                    else:
                        # Execute the tool
                        try:
                            # Ensure address has 0x prefix if tool requires it (based on previous findings)
                            if tool_name in ["ghidra_rename_function_by_address", "ghidra_decompile_function_by_address", "ghidra_set_decompiler_comment", "ghidra_set_disassembly_comment"]:
                                addr_key = 'address' if 'address' in parameters else 'function_address' # Handle potential variations
                                if addr_key in parameters:
                                     addr_val = parameters[addr_key]
                                     if isinstance(addr_val, str) and not addr_val.startswith('0x') and addr_val.isalnum():
                                          parameters[addr_key] = "0x" + addr_val
                                          logger.info(f"Executor Handler: Added '0x' prefix to address for tool '{tool_name}'. New params: {parameters}")
                                
                            logger.info(f"Executor Handler: Executing tool '{tool_name}' from plan with params: {parameters}")
                            result = tool_func(**parameters)
                            # Store the raw result, subsequent agents will interpret it
                            tool_result = result # Use the direct result dict {'status': ..., 'result': ...} or {'status': ..., 'message': ...}
                            logger.info(f"Executor Handler: Tool '{tool_name}' executed. Result status: {tool_result.get('status')}")

                        except Exception as exec_e:
                            logger.error(f"Executor Handler: Error executing tool '{tool_name}'. Error: {exec_e}", exc_info=True)
                            tool_result = {"status": "error", "message": f"Error executing {tool_name}: {str(exec_e)}", "tool": tool_name}
            
            # If tool was processed (meaning we entered the 'else' block for non-empty plan),
            # remove the first item from the plan list in the state.
            # This happens regardless of tool success/failure/not_found.
            if current_state and "ghidra_plan" in current_state and isinstance(current_state["ghidra_plan"], list) and len(current_state["ghidra_plan"]) > 0:
                # Make sure tool_name was actually set before logging removal
                removed_tool_name = tool_name if tool_name else "(invalid item)"
                current_state["ghidra_plan"] = current_state["ghidra_plan"][1:]
                logger.info(f"Executor Handler: Removed tool '{removed_tool_name}' from plan. Remaining: {len(current_state['ghidra_plan'])}")

        # --- Update State --- 
        if tool_result is not None:
            # Ensure the result has a status, default to error if missing
            if not isinstance(tool_result, dict) or 'status' not in tool_result:
                 logger.warning(f"Executor Handler: Tool '{tool_name if 'tool_name' in locals() and tool_name else 'unknown'}' returned unexpected result format: {tool_result}. Wrapping as error.")
                 tool_result = {"status": "error", "message": f"Tool returned unexpected format: {str(tool_result)[:200]}", "tool": tool_name if 'tool_name' in locals() and tool_name else 'unknown'}
            current_state['last_tool_result'] = tool_result
            logger.debug(f"Executor Handler: Updated state['last_tool_result'] = {str(tool_result)[:500]}") # Log truncated result
        else:
             # This case might be reached if the plan item was invalid but tool_result wasn't explicitly set
             logger.warning("Executor Handler: tool_result was None after processing. Setting generic error.")
             current_state['last_tool_result'] = {"status": "error", "message": "Internal error: Tool result processing failed in handler."}

    except Exception as e:
        # Catch any unexpected errors during handler execution
        logger.error(f"Executor Handler: Unhandled exception: {str(e)}", exc_info=True)
        if current_state:
            current_state['last_tool_result'] = {"status": "error", "message": f"Critical error in executor handler: {str(e)}"}
        
    # IMPORTANT: after_model_callback must return None or an LlmResponse.
    return None


# Modify the executor agent to use our handler
tool_executor_agent.after_model_callback = handle_executor_response

# --- Runner Function REMOVED --- 
# def run_ghidra_analysis_sync(...): ... 

# ... (build_ghidra_analyzer_pipeline function remains) ...

# --- __main__ block REMOVED --- 
# if __name__ == '__main__': ... 