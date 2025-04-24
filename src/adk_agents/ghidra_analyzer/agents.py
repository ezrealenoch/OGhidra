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
from pydantic import BaseModel, Field # <-- Add BaseModel import

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

# Modified planner instruction to be less proactive
PLANNER_INSTRUCTION_ROBUST = f"""
You are the Planning Agent for a Ghidra analysis task.

**IMPORTANT FIRST STEP:** Check the 'user_query'. If the query is EXACTLY the text "EXIT LOOP", 
respond with: {{"exit_loop": true}}

If the query is NOT "EXIT LOOP", proceed with the following planning task:
Your goal is to analyze the user's query and the current state (including past tool results and analysis)
and create a **minimal step-by-step plan** of Ghidra tool calls required to **directly gather the information requested by the user_query**.

Available Tools (Use EXACT names and provide ONLY the required parameters):
{_format_tool_list_for_prompt(ALL_GHIDRA_TOOLS)}

Input State Keys:
- user_query: The original request from the user.
- last_tool_result (optional): The result from the previous tool execution, including status ('success' or 'error') and result/message.
- current_analysis (optional): The analysis synthesized so far.
- ghidra_plan (optional): The existing plan (list of dictionaries), if refining (usually based on Reviewer feedback).

**CRITICAL PLANNING RULES**:
- Generate the *minimum* number of tool calls necessary to directly answer the `user_query`.
- Do **NOT** plan for deeper analysis (like decompilation of all functions) unless the `user_query` specifically asks for it OR the Reviewer agent has explicitly requested a revised plan with instructions for deeper analysis.
- If the query is simply to list items (e.g., "list functions"), your plan should contain ONLY the corresponding listing tool call (e.g., `ghidra_list_functions`).
- Your response MUST be in JSON format.
- For queries that are NOT "EXIT LOOP", output a JSON list of dictionaries, where each dictionary represents a single tool call.
- Each dictionary MUST have 'tool_name' and 'parameters' (a dictionary of arguments for that specific tool).
- If a tool takes no arguments, the 'parameters' dictionary MUST be empty: {{}}.
- If no tool calls are needed based on the query and current state (e.g., query already answered), output an empty list: [].

Example response for query "List functions":
[
  {{"tool_name": "ghidra_list_functions", "parameters": {{}}}}
]

Example response for query "Decompile main":
[
  {{"tool_name": "ghidra_decompile_function_by_name", "parameters": {{"function_name": "main"}}}}
]

Example response for "EXIT LOOP" query:
{{"exit_loop": true}}

DO NOT explain your reasoning or add any text before or after the JSON.
ONLY respond with the JSON array of tool calls or the exit_loop object.
"""

# 1. Planning Agent - Modified to be less proactive
planning_agent = LlmAgent(
    name="Planner",
    model=LLM_INSTANCE,
    instruction=PLANNER_INSTRUCTION_ROBUST,
    output_key="ghidra_plan" 
)

# 2. Tool Execution Agent - No changes needed here, handler bypasses LLM
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

# 3. Analysis Agent - Modified to include results directly
ANALYZER_INSTRUCTION_STRICT = """
You are the Analysis Agent for a Ghidra binary analysis task.

Your role is to analyze the outputs from Ghidra tools (`last_tool_result`) and provide insights, updating `current_analysis`.

IMPORTANT:
- Return only plain text analysis. DO NOT return JSON, function calls, or tool usage suggestions.
- Analyze ONLY what has been discovered via the tools. Do not speculate or suggest future steps.
- **If the last tool was 'ghidra_list_functions' and it was successful, your analysis MUST begin with the exact phrase 'The following functions were found:' followed by a newline and then the list of functions from the tool result's 'result' field. You may add a brief summary sentence after the list.**
- **Similarly, if the last tool was 'ghidra_decompile_function_by_address' or 'ghidra_decompile_function_by_name' and was successful, include the decompiled code from the 'result' field in your analysis, perhaps indicating which function it belongs to.**

Input state:
- user_query: The original user query (for context only).
- last_tool_result: The most recent tool execution result (check 'status' and 'result' fields).
- current_analysis: The analysis synthesized so far (build upon this if appropriate, but focus on the latest result).
- ghidra_plan: The remaining plan items (for context only).

Guidelines:
1. Focus analysis *strictly* on the data provided in `last_tool_result`.
2. If `last_tool_result` indicates an error, describe the error message.
3. Build upon `current_analysis` only if synthesizing multiple results. If processing a single result, start fresh or clearly delineate the new findings.
4. Use clear, concise language, prioritizing accuracy.

Return ONLY the textual analysis to be stored in `current_analysis`.
"""

analysis_agent = LlmAgent(
    name="Analyzer",
    model=LLM_INSTANCE,
    instruction=ANALYZER_INSTRUCTION_STRICT,
    output_key="current_analysis"
)

# --- Reviewer Agent Schema and Prompt ---

class ReviewerDecision(BaseModel):
    """Schema for the Reviewer agent's structured output."""
    directive: str = Field(description="The chosen directive: CONTINUE, REVISE_PLAN, FINAL_ANSWER, or EXIT_LOOP.")
    reason: str = Field(description="A brief explanation for the chosen directive.")
    # ADK's LoopAgent should recognize 'escalate' in EventActions, which can be influenced by output schema mapping
    # Let's map the decision directly to an 'escalate' flag.
    escalate: bool = Field(default=False, description="Set to true if directive is FINAL_ANSWER or EXIT_LOOP to stop the loop.")

REVIEWER_INSTRUCTION_STRUCTURED = f"""
You are the Review Agent for a Ghidra binary analysis task.

Your role is to evaluate the current state and determine the **single next action** based on the original `user_query`.
Output your decision as a JSON object conforming to the following schema:

```json
{{
  "directive": "CONTINUE | REVISE_PLAN | FINAL_ANSWER | EXIT_LOOP",
  "reason": "Brief explanation for the directive.",
  "escalate": true | false
}}
```

**CRITICAL: Evaluate completion based *only* on the original `user_query`. Has the information *explicitly requested* by the user been provided in `current_analysis` or `last_tool_result`?**

Input State:
- user_query: The original user question. **Adhere strictly to this query's scope.**
- current_analysis: Analysis generated by the Analysis Agent.
- ghidra_plan: The remaining planned tool calls. An empty list means the current plan is finished.
- last_tool_result: The most recent tool execution result (check status: 'success' or 'error').

**Decision Logic & Output Format:**

1.  **CONTINUE:** If the current `ghidra_plan` is **not empty** and the last tool executed successfully (`last_tool_result['status'] == 'success'`), continue executing the plan.
    JSON Output: `{{"directive": "CONTINUE", "reason": "Proceeding with planned steps.", "escalate": false}}`

2.  **REVISE_PLAN:** If `last_tool_result` indicates an error or the `current_analysis` reveals that the current plan is insufficient or incorrect for the `user_query`.
    JSON Output: `{{"directive": "REVISE_PLAN", "reason": "<Explain why plan needs revision>", "escalate": false}}`

3.  **FINAL_ANSWER:** If the `user_query` has been **fully and directly addressed** by the information now present in `current_analysis` (or `last_tool_result` if analysis is simple), and the `ghidra_plan` is empty. Do **NOT** proceed with deeper analysis if the user didn't ask for it.
    JSON Output: `{{"directive": "FINAL_ANSWER", "reason": "<Explain how query is answered>", "escalate": true}}`

4.  **EXIT_LOOP:** If analysis seems impossible, tools are consistently failing, or the `user_query` cannot be answered.
    JSON Output: `{{"directive": "EXIT_LOOP", "reason": "<Explain reason for exiting>", "escalate": true}}`

**Decision Logic Summary:**
- Is plan non-empty & last tool OK? -> CONTINUE, escalate: false
- Did last tool fail OR plan wrong? -> REVISE_PLAN, escalate: false
- Is plan empty AND query satisfied? -> FINAL_ANSWER, escalate: true
- Is task impossible/failing? -> EXIT_LOOP, escalate: true

Return ONLY the JSON object representing your decision. Do not add any other text.
"""

review_agent = LlmAgent(
    name="Reviewer",
    model=LLM_INSTANCE,
    instruction=REVIEWER_INSTRUCTION_STRUCTURED, # Use new structured prompt
    output_schema=ReviewerDecision,             # Set the output schema
    output_key="reviewer_decision"              # Store the structured output here
    # NO after_agent_callback needed anymore
)

# --- Main Loop Agent ---

# Define the loop agent using the sub-agents in sequence
agent = LoopAgent(
    name="ghidra_analyzer", # This name should match the directory/module name
    sub_agents=[
        planning_agent,
        tool_executor_agent,
        analysis_agent,
        review_agent # Reviewer is last
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
             # Avoid modifying state if we couldn't retrieve it
             return None # Must return None from callback

        # --- Process ghidra_plan from State --- 
        ghidra_plan = current_state.get('ghidra_plan', [])

        # Ensure ghidra_plan is a list (it might be a JSON string from Planner initially)
        if isinstance(ghidra_plan, str):
            try:
                ghidra_plan = json.loads(ghidra_plan)
                if not isinstance(ghidra_plan, list):
                     logger.warning(f"Executor Handler: Parsed ghidra_plan from string, but it's not a list: {{type(ghidra_plan)}}")
                     ghidra_plan = [] # Treat as invalid plan
                else:
                     logger.info("Executor Handler: Successfully parsed ghidra_plan from JSON string in state.")
                     # Update state with the parsed list
                     current_state['ghidra_plan'] = ghidra_plan 
            except json.JSONDecodeError:
                logger.error(f"Executor Handler: ghidra_plan in state was a string but failed to parse as JSON: '{{ghidra_plan[:100]}}...'")
                ghidra_plan = [] # Treat as invalid plan

        if not isinstance(ghidra_plan, list):
            logger.error(f"Executor Handler: ghidra_plan in state is not a list or valid JSON string. Type: {{type(ghidra_plan)}}. Value: {{str(ghidra_plan)[:100]}}...")
            tool_result = {"status": "error", "message": f"Internal error: Invalid ghidra_plan format in state ({{type(ghidra_plan)}})."}
            ghidra_plan = [] # Reset plan to prevent further errors in this handler run

        # --- Determine Action based on Plan --- 
        if not ghidra_plan: 
            logger.info("Executor Handler: ghidra_plan is empty or invalid.")
            if tool_result is None: # Only set no_plan if not already an error
                tool_result = {"status": "no_plan", "message": "No tool calls remaining in plan or plan was invalid."}
        else:
            # Get the first planned tool call
            next_tool_call = ghidra_plan[0]
            tool_name = None 
            if not isinstance(next_tool_call, dict):
                logger.error(f"Executor Handler: First item in ghidra_plan is not a dictionary: {{next_tool_call}}")
                tool_result = {"status": "error", "message": f"Internal error: Invalid item format in ghidra_plan."}
            else:
                tool_name = next_tool_call.get("tool_name")
                parameters = next_tool_call.get("parameters", {})

                if not tool_name:
                    tool_result = {"status": "error", "message": "Plan item missing 'tool_name'."}
                # --- REMOVED exit_loop handling here - let Planner/Reviewer handle loop termination ---
                # elif tool_name == "exit_loop": ... 
                else:
                    # Find and execute the actual tool
                    tool_func = None
                    for tool in ALL_GHIDRA_TOOLS:
                        if tool.name == tool_name:
                            tool_func = tool.func
                            break

                    if tool_func is None:
                        tool_result = {"status": "error", "message": f"Tool '{{tool_name}}' specified in plan not found.", "tool": tool_name}
                    else:
                        # Execute the tool
                        try:
                            # Address prefix logic... (remains the same)
                            if tool_name in ["ghidra_rename_function_by_address", "ghidra_decompile_function_by_address", "ghidra_set_decompiler_comment", "ghidra_set_disassembly_comment"]:
                                addr_key = 'address' if 'address' in parameters else 'function_address' 
                                if addr_key in parameters:
                                     addr_val = parameters[addr_key]
                                     if isinstance(addr_val, str) and not addr_val.startswith('0x') and addr_val.isalnum():
                                          parameters[addr_key] = "0x" + addr_val
                                          logger.info(f"Executor Handler: Added '0x' prefix to address for tool '{{tool_name}}'. New params: {{parameters}}")
                                
                            logger.info(f"Executor Handler: Executing tool '{{tool_name}}' from plan with params: {{parameters}}")
                            result = tool_func(**parameters)
                            tool_result = result 
                            logger.info(f"Executor Handler: Tool '{{tool_name}}' executed. Result status: {{tool_result.get('status')}}")

                        except Exception as exec_e:
                            logger.error(f"Executor Handler: Error executing tool '{{tool_name}}'. Error: {{exec_e}}", exc_info=True)
                            tool_result = {"status": "error", "message": f"Error executing {{tool_name}}: {{str(exec_e)}}", "tool": tool_name}
            
            # Remove the processed tool call from the plan
            if current_state and "ghidra_plan" in current_state and isinstance(current_state["ghidra_plan"], list) and len(current_state["ghidra_plan"]) > 0:
                removed_tool_name = tool_name if tool_name else "(invalid item)"
                current_state["ghidra_plan"] = current_state["ghidra_plan"][1:]
                logger.info(f"Executor Handler: Removed tool '{{removed_tool_name}}' from plan. Remaining: {{len(current_state['ghidra_plan'])}}")

        # --- Update State --- 
        if tool_result is not None:
            if not isinstance(tool_result, dict) or 'status' not in tool_result:
                 logger.warning(f"Executor Handler: Tool '{{tool_name if 'tool_name' in locals() and tool_name else 'unknown'}}' returned unexpected result format: {{tool_result}}. Wrapping as error.")
                 tool_result = {"status": "error", "message": f"Tool returned unexpected format: {{str(tool_result)[:200]}}", "tool": tool_name if 'tool_name' in locals() and tool_name else 'unknown'}
            current_state['last_tool_result'] = tool_result
            logger.debug(f"Executor Handler: Updated state['last_tool_result'] = {{str(tool_result)[:500]}}") 
        else:
             logger.warning("Executor Handler: tool_result was None after processing. Setting generic error.")
             current_state['last_tool_result'] = {"status": "error", "message": "Internal error: Tool result processing failed in handler."}

    except Exception as e:
        logger.error(f"Executor Handler: Unhandled exception: {{str(e)}}", exc_info=True)
        if current_state: # Check if current_state was successfully retrieved before trying to modify it
            current_state['last_tool_result'] = {"status": "error", "message": f"Critical error in executor handler: {{str(e)}}"}
        
    return None


# Modify the executor agent to use our handler
tool_executor_agent.after_model_callback = handle_executor_response

# --- Runner Function REMOVED --- 
# def run_ghidra_analysis_sync(...): ... 

# ... (build_ghidra_analyzer_pipeline function remains) ...

# --- __main__ block REMOVED --- 
# if __name__ == '__main__': ... 