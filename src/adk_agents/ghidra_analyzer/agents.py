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
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from google.adk.agents import LlmAgent, LoopAgent, BaseAgent
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
            params_dict = tool.func.__annotations__
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

# Regenerate the planner instruction with the potentially improved formatting
# AND add the check for "EXIT LOOP"
PLANNER_INSTRUCTION_WITH_EXIT = f"""
You are the Planning Agent for a Ghidra analysis task.

**IMPORTANT FIRST STEP:** Check the 'user_query'. If the query is EXACTLY the text "EXIT LOOP", then you MUST call the `exit_loop` tool immediately and do nothing else. 

If the query is NOT "EXIT LOOP", proceed with the following planning task:
Your goal is to analyze the user's query and the current state (including past tool results and analysis) 
and create a step-by-step plan of Ghidra tool calls required to gather the necessary information.

Available Tools (Use EXACT names and provide ONLY the required parameters):
`exit_loop()`: Immediately stops the entire agent process. Use ONLY if the user query is exactly "EXIT LOOP".
{_format_tool_list_for_prompt(ALL_GHIDRA_TOOLS)}

Input State Keys:
- user_query: The original request from the user.
- last_tool_result (optional): The result from the previous tool execution, including status ('success' or 'error') and result/message.
- current_analysis (optional): The analysis synthesized so far.
- ghidra_plan (optional): The existing plan (list of dictionaries), if refining.

Output (only if query is NOT "EXIT LOOP"):
- You MUST output a JSON list of dictionaries, where each dictionary represents a single tool call.
- Each dictionary MUST have 'tool_name' and 'parameters' (a dictionary of arguments for that specific tool).
- If a tool takes no arguments, the 'parameters' dictionary MUST be empty: {{}}.
- Store this list in the 'ghidra_plan' state key.
- If no tool calls are needed based on the query and state, output an empty list: [].
- Base your plan on the user_query. If last_tool_result indicates an error, consider if the plan needs adjustment.

Example Output (for 'ghidra_plan'):
[ 
  {{"tool_name": "ghidra_list_functions", "parameters": {{}}}},  # Correct: No parameters
  {{"tool_name": "ghidra_decompile_function_by_name", "parameters": {{"function_name": "main"}}}} # Correct: Required parameter
]

Remember: First check for "EXIT LOOP" in the user_query. If found, call `exit_loop()`. Otherwise, analyze the query and state, then generate the plan.
"""

# 1. Planning Agent
planning_agent = LlmAgent(
    name="Planner",
    model=LLM_INSTANCE,
    instruction=PLANNER_INSTRUCTION_WITH_EXIT, # Use updated instruction
    # tools=[exit_loop] + ALL_GHIDRA_TOOLS, # REMOVED - Planner should not declare tools it doesn't execute directly
    output_key="ghidra_plan" # Output the plan to this state key
)

# 2. Tool Execution Agent
# Simplified instruction, reinforced to use only provided params
EXECUTOR_INSTRUCTION_SIMPLE = """
Execute the first tool call listed in the 'ghidra_plan' state variable.
Use the tool name and parameters *exactly* as specified in that list entry. Do NOT add any extra parameters.
Store the complete result dictionary in 'last_tool_result'.
Update 'ghidra_plan' by removing the executed step.
Respond only with a brief confirmation message stating the tool executed and the result status (e.g., 'Executed ghidra_list_functions. Status: success.').
"""
tool_executor_agent = LlmAgent(
    name="Executor",
    model=LLM_INSTANCE,
    instruction=EXECUTOR_INSTRUCTION_SIMPLE,
    include_contents='none',
    tools=ALL_GHIDRA_TOOLS, # RESTORED - Executor needs tools to execute the plan
    # Output key handled by framework state manipulation
)

# 3. Analysis Agent
ANALYZER_INSTRUCTION_STRICT = """
You are the Analysis Agent.
Your ONLY task is to examine the dictionary stored in the 'last_tool_result' state key.

1. Check the 'status' field within 'last_tool_result'.
2. If 'status' is 'success', extract the value associated with the 'result' key.
3. If 'status' is 'error', extract the value associated with the 'message' key.
4. Retrieve the original query from the 'user_query' state key.
5. Retrieve the existing analysis from the 'current_analysis' state key (if it exists).
6. Synthesize a new analysis by combining the existing 'current_analysis' with the extracted 'result' or 'message' from 'last_tool_result', relating it back to the 'user_query'.
7. Store this complete, updated analysis text into the 'current_analysis' state key, overwriting the previous value.
8. Focus *only* on information present in the 'last_tool_result', 'user_query', and 'current_analysis' state keys. Ignore any other context provided.
9. CRITICAL: Your entire response MUST be plain text only. Do NOT output JSON, do NOT output markdown, and absolutely DO NOT attempt to call any tools or functions.

Example Output (for 'current_analysis' state key - PLAIN TEXT):
Based on the query 'analyze function main':
- Tool ghidra_list_functions succeeded. Result: [list of functions]
- Tool ghidra_decompile_function_by_name failed with error: Function not found.
"""
analysis_agent = LlmAgent(
    name="Analyzer",
    model=LLM_INSTANCE,
    instruction=ANALYZER_INSTRUCTION_STRICT,
    output_key="current_analysis"
)

# 4. Review Agent
review_agent = LlmAgent(
    name="Reviewer",
    model=LLM_INSTANCE,
    instruction="""
You are the Review Agent.
Your role is to check if the Ghidra analysis task is complete and the user query is answered.

Input State Keys:
- user_query: The original user query.
- ghidra_plan: The list of remaining planned tool calls.
- current_analysis: The accumulated analysis so far.
- last_tool_result (optional): The result of the very last tool call.

Decision Logic:
1. Examine the 'ghidra_plan'. If it is NOT empty, the task is not finished. Respond with a brief status update like "Plan execution ongoing."
2. If the 'ghidra_plan' IS empty, evaluate the 'current_analysis'. Does it sufficiently answer the 'user_query'? Consider any errors noted.
3. If the plan is empty AND the query is answered: Respond ONLY with the exact word "STOP".
4. If the plan is empty BUT the query is NOT answered: Respond with feedback for the Planner, e.g., "Analysis generated: [brief summary of current_analysis]. Query requires more detail on X. Planning needed."

Output:
- If task is complete: The single word "STOP".
- Otherwise: A status message or feedback for the Planner.
""",
    # This agent's primary output determines loop continuation.
    # The final answer is implicitly in the 'current_analysis' state when Reviewer returns 'STOP'.
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

# --- Runner Function (Optional - for testing) ---

def run_ghidra_analysis_sync(user_query: str) -> Dict[str, Any]:
    """
    Synchronous wrapper to run the Ghidra analyzer loop.
    Note: ADK execution is inherently async. This is a convenience wrapper.
    Requires Python 3.7+ for asyncio.run.
    """
    logger.info(f"Starting Ghidra analysis for query: {user_query}")
    initial_state = {
        "user_query": user_query,
        "ghidra_plan": [],
        "last_tool_result": None,
        "current_analysis": ""
    }

    async def _run():
        final_state_snapshot = initial_state.copy()
        final_text_response = "Agent loop did not produce a final response."
        
        async for event in agent.run_async(initial_state=initial_state, query=user_query):
            logger.debug(f"Agent Event: {event.author} | Final: {event.is_final_response} | State: {getattr(event, 'state', {} )} | Text: {event.get_text()}")
            # Capture the state from the last event (might be final or last before stop)
            if hasattr(event, 'state'):
                final_state_snapshot.update(event.state) 
            if event.is_final_response:
                final_text_response = event.get_text()
                # If reviewer said STOP, the final answer is in the state
                if final_text_response == "STOP":
                    final_text_response = final_state_snapshot.get('current_analysis', "Analysis complete (STOP signal received).")
                break
        
        # Add the final textual response to the state dictionary
        final_state_snapshot['final_response'] = final_text_response
        return final_state_snapshot
        
    try:
        # Use asyncio.run() for the top-level async call
        result_state = asyncio.run(_run())
        logger.info(f"Ghidra analysis finished.")
        # logger.debug(f"Final State: {result_state}")
        return result_state
    except Exception as e:
        logger.error(f"Error running Ghidra analysis loop: {e}", exc_info=True)
        return {"status": "error", "message": str(e), "current_analysis": initial_state.get("current_analysis", ""), "ghidra_plan": initial_state.get("ghidra_plan", []) }

if __name__ == '__main__':
    # Example of running the analysis directly
    # Ensure GhidraMCP server is running before executing this!
    logging.basicConfig(level=logging.INFO) # Ensure logging is configured
    # test_query = "List all functions."
    test_query = "Decompile the function named main and tell me what it does."
    # test_query = "What is the function at 0x401000? Decompile it."
    # test_query = "Add a comment \"Entry point here\" to the decompiler view at the address of the function named entry."
    
    final_result = run_ghidra_analysis_sync(test_query)
    
    print("\n--- Analysis Complete ---")
    print(f"Query: {test_query}")
    if final_result.get("status") == "error":
        print(f"Error: {final_result.get('message')}")
    else:
        # Prefer 'current_analysis' as it holds the synthesized result before STOP
        print(f"Final Analysis/Response:\n{final_result.get('current_analysis', final_result.get('final_response', 'N/A'))}")
        
    # Optional: Print full state for debugging
    # print("\nFull Final State:")
    # print(json.dumps(final_result, indent=2)) 