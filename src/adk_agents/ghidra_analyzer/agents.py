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
EXECUTOR_INSTRUCTION_ROBUST = """
You are the Tool Execution Agent for a Ghidra analysis task.

Your task is to:
1. Examine the 'ghidra_plan' state key, which contains a list of planned tool calls.
2. If the list is empty, respond with: {"status": "no_plan", "message": "No tool calls in plan."}
3. If the list contains an object with {"exit_loop": true}, call the exit_loop() function.
4. Otherwise, take the first tool call from the list and execute it exactly as specified.

For executing a tool call:
- Extract the 'tool_name' and 'parameters' from the first item in the ghidra_plan list.
- Execute the specified tool with the exact parameters provided.
- Create a result dictionary: {"status": "success", "data": result} or {"status": "error", "message": error_message}
- Store this result dictionary in 'last_tool_result' state key.
- Update 'ghidra_plan' by removing the executed step.
- Respond with a JSON object: {"status": "executed", "tool": tool_name, "success": true/false}

Example Response:
{"status": "executed", "tool": "ghidra_list_functions", "success": true}

ONLY respond with JSON. DO NOT add any explanation or text before or after the JSON.
"""

tool_executor_agent = LlmAgent(
    name="Executor",
    model=LLM_INSTANCE,
    instruction=EXECUTOR_INSTRUCTION_ROBUST,
    include_contents='none',
    tools=[exit_loop] + ALL_GHIDRA_TOOLS,  # Include the exit_loop tool
)

# 3. Analysis Agent - Keep this one mostly the same but reinforce JSON avoidance
ANALYZER_INSTRUCTION_STRICT = """
You are the Analysis Agent.
Your ONLY task is to examine the dictionary stored in the 'last_tool_result' state key.

1. Check the 'status' field within 'last_tool_result'.
2. If 'status' is 'success', extract the value associated with the 'data' key.
3. If 'status' is 'error', extract the value associated with the 'message' key.
4. Retrieve the original query from the 'user_query' state key.
5. Retrieve the existing analysis from the 'current_analysis' state key (if it exists).
6. Synthesize a new analysis by combining the existing 'current_analysis' with the extracted data or error message from 'last_tool_result', relating it back to the 'user_query'.
7. Store this complete, updated analysis text into the 'current_analysis' state key, overwriting the previous value.

CRITICAL: Your entire response MUST be plain text only. Do NOT output JSON, do NOT use markdown formatting, and absolutely DO NOT attempt to call any tools or functions.

Example Output (PLAIN TEXT ONLY):
Based on the query 'analyze function main':
- Tool ghidra_list_functions succeeded. Found the following functions: main, printf, malloc, free
- The decompilation reveals main calls printf and malloc functions.
"""
analysis_agent = LlmAgent(
    name="Analyzer",
    model=LLM_INSTANCE,
    instruction=ANALYZER_INSTRUCTION_STRICT,
    output_key="current_analysis"
)

# 4. Review Agent - Keep this one mostly the same
REVIEWER_INSTRUCTION = """
You are the Review Agent.
Your role is to check if the Ghidra analysis task is complete and the user query is answered.

Input State Keys:
- user_query: The original user query.
- ghidra_plan: The list of remaining planned tool calls.
- current_analysis: The accumulated analysis so far.
- last_tool_result (optional): The result of the very last tool call.

Decision Logic:
1. Examine the 'ghidra_plan'. If it is NOT empty, the task is not finished. Respond with: "Plan execution ongoing."
2. If the 'ghidra_plan' IS empty, evaluate the 'current_analysis'. Does it sufficiently answer the 'user_query'?
3. If the plan is empty AND the query is answered: Respond ONLY with the exact word "STOP".
4. If the plan is empty BUT the query is NOT answered: Respond with: "Analysis incomplete. Additional planning needed."

Your response MUST be just a simple string with no JSON or special formatting.
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

def build_ghidra_analyzer_pipeline(llm=None):
    """
    Build a Ghidra analyzer pipeline with optional custom LLM.
    
    Args:
        llm: Custom LLM model to use instead of the default.
             If None, uses the configured LLM_INSTANCE.
    
    Returns:
        LoopAgent: Configured Ghidra analyzer pipeline
    """
    model = llm if llm is not None else LLM_INSTANCE
    
    # Create agents with the provided model
    planning = LlmAgent(
        name="Planner",
        model=model,
        instruction=PLANNER_INSTRUCTION_ROBUST,
        output_key="ghidra_plan"
    )
    
    executor = LlmAgent(
        name="Executor",
        model=model,
        instruction=EXECUTOR_INSTRUCTION_ROBUST,
        include_contents='none',
        tools=[exit_loop] + ALL_GHIDRA_TOOLS,
    )
    
    analyzer = LlmAgent(
        name="Analyzer",
        model=model,
        instruction=ANALYZER_INSTRUCTION_STRICT,
        output_key="current_analysis"
    )
    
    reviewer = LlmAgent(
        name="Reviewer",
        model=model,
        instruction=REVIEWER_INSTRUCTION,
    )
    
    # Create and return the loop agent
    return LoopAgent(
        name="ghidra_analyzer",
        sub_agents=[planning, executor, analyzer, reviewer],
        max_iterations=10,
        description="An agent that analyzes Ghidra projects by planning and executing Ghidra tool calls."
    )

if __name__ == '__main__':
    # Example of running the analysis directly
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create the Ghidra analyzer pipeline
    ghidra_analyzer = build_ghidra_analyzer_pipeline()
    
    # Get the query from command line or use default
    query = sys.argv[1] if len(sys.argv) > 1 else "List all functions in the current program and describe what they do"
    
    # Run the analysis
    result = ghidra_analyzer.execute({"user_query": query})
    
    # Print the result
    print("\n=== ANALYSIS RESULT ===")
    print(result.get("current_analysis", "No analysis generated")) 