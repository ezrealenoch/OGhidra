"""
Tests for the Ghidra analyzer agent.

These tests verify that the Ghidra analyzer agent can correctly:
1. List all functions in a binary
2. Explain what a function does
3. Recursively traverse functions from the entry point
4. Rename a function based on its behavior

Note: These tests use mock implementations of the Ghidra tools to avoid 
needing a live Ghidra server.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the src directory to the path so we can import the agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock data for functions
MOCK_FUNCTIONS = [
    {
        "name": "main",
        "address": "0x00401000",
        "signature": "int main(int argc, char **argv)",
        "description": "Entry point of the program"
    },
    {
        "name": "process_input",
        "address": "0x00401100",
        "signature": "int process_input(char *input, size_t length)",
        "description": "Processes user input data"
    },
    {
        "name": "validate_user",
        "address": "0x00401200",
        "signature": "bool validate_user(char *username, char *password)",
        "description": "Validates user credentials"
    },
    {
        "name": "read_file",
        "address": "0x00401300",
        "signature": "char* read_file(const char *filename)",
        "description": "Reads file contents into memory"
    }
]

# Mock decompiled code for each function
MOCK_DECOMPILED_CODE = {
    "main": """
int main(int argc, char **argv) {
    char input[256];
    if (argc < 2) {
        printf("Usage: %s <input_file>\\n", argv[0]);
        return 1;
    }
    
    char *data = read_file(argv[1]);
    if (data == NULL) {
        printf("Error reading file\\n");
        return 1;
    }
    
    if (!validate_user("admin", "password123")) {
        printf("Authentication failed\\n");
        free(data);
        return 1;
    }
    
    int result = process_input(data, strlen(data));
    printf("Result: %d\\n", result);
    
    free(data);
    return 0;
}
""",
    "process_input": """
int process_input(char *input, size_t length) {
    int count = 0;
    
    for (size_t i = 0; i < length; i++) {
        if (input[i] == '\\n') {
            count++;
        }
    }
    
    return count;
}
""",
    "validate_user": """
bool validate_user(char *username, char *password) {
    if (strcmp(username, "admin") != 0) {
        return false;
    }
    
    if (strcmp(password, "password123") != 0) {
        return false;
    }
    
    return true;
}
""",
    "read_file": """
char* read_file(const char *filename) {
    FILE *fp = fopen(filename, "r");
    if (fp == NULL) {
        return NULL;
    }
    
    fseek(fp, 0, SEEK_END);
    long file_size = ftell(fp);
    rewind(fp);
    
    char *buffer = (char*)malloc(file_size + 1);
    if (buffer == NULL) {
        fclose(fp);
        return NULL;
    }
    
    size_t read_size = fread(buffer, 1, file_size, fp);
    buffer[read_size] = '\\0';
    
    fclose(fp);
    return buffer;
}
"""
}

# Mock data for function calls
MOCK_CALLED_FUNCTIONS = {
    "main": [
        {"name": "printf", "address": "0x00401500"},
        {"name": "read_file", "address": "0x00401300"},
        {"name": "validate_user", "address": "0x00401200"},
        {"name": "process_input", "address": "0x00401100"},
        {"name": "free", "address": "0x00401600"}
    ],
    "process_input": [],
    "validate_user": [
        {"name": "strcmp", "address": "0x00401700"}
    ],
    "read_file": [
        {"name": "fopen", "address": "0x00401800"},
        {"name": "fseek", "address": "0x00401900"},
        {"name": "ftell", "address": "0x00401a00"},
        {"name": "rewind", "address": "0x00401b00"},
        {"name": "malloc", "address": "0x00401c00"},
        {"name": "fread", "address": "0x00401d00"},
        {"name": "fclose", "address": "0x00401e00"}
    ]
}

# Mock data for function references
MOCK_FUNCTION_REFS = {
    "main": [],
    "process_input": [
        {"name": "main", "address": "0x00401000"}
    ],
    "validate_user": [
        {"name": "main", "address": "0x00401000"}
    ],
    "read_file": [
        {"name": "main", "address": "0x00401000"}
    ]
}

def setup_mock_tool_calls():
    """Set up mock implementations for Ghidra tool functions"""
    
    # Mock function list
    def mock_list_functions(*args, **kwargs):
        return json.dumps(MOCK_FUNCTIONS)
    
    # Mock decompile function by name
    def mock_decompile_function_by_name(function_name, *args, **kwargs):
        if function_name in MOCK_DECOMPILED_CODE:
            return MOCK_DECOMPILED_CODE[function_name]
        return "// Function not found"
    
    # Mock get function by address
    def mock_get_function_by_address(address, *args, **kwargs):
        for func in MOCK_FUNCTIONS:
            if func["address"] == address:
                return json.dumps(func)
        return "{}"
    
    # Mock get called functions
    def mock_get_called_functions(function_name, *args, **kwargs):
        if function_name in MOCK_CALLED_FUNCTIONS:
            return json.dumps(MOCK_CALLED_FUNCTIONS[function_name])
        return "[]"
    
    # Mock get function references
    def mock_get_function_references(function_name, *args, **kwargs):
        if function_name in MOCK_FUNCTION_REFS:
            return json.dumps(MOCK_FUNCTION_REFS[function_name])
        return "[]"
    
    # Mock rename function
    def mock_rename_function(function_name, new_name, *args, **kwargs):
        return json.dumps({"status": "success", "old_name": function_name, "new_name": new_name})
    
    # Create a dictionary of mock functions
    mock_functions = {
        "ghidra_list_functions": mock_list_functions,
        "ghidra_decompile_function_by_name": mock_decompile_function_by_name,
        "ghidra_get_function_by_address": mock_get_function_by_address,
        "ghidra_get_called_functions": mock_get_called_functions,
        "ghidra_get_function_references": mock_get_function_references,
        "ghidra_rename_function": mock_rename_function
    }
    
    return mock_functions

class TestGhidraAnalyzer(unittest.TestCase):
    """Test cases for the Ghidra analyzer agent"""
    
    @unittest.skip("Requires full ADK setup with LiteLLM")
    def test_list_functions(self):
        """Test if the agent can list all functions in a binary"""
        from src.adk_agents.ghidra_analyzer.agents import build_ghidra_analyzer_pipeline
        
        # Mock the tools and agent response
        with patch('src.adk_tools.ghidra_mcp') as mock_ghidra:
            mock_tools = setup_mock_tool_calls()
            for name, func in mock_tools.items():
                setattr(mock_ghidra, name, func)
            
            # Set up the agent pipeline with mock LLM
            mock_llm = MagicMock()
            mock_llm.generate.return_value = "The binary contains the following functions: main, process_input, validate_user, read_file"
            
            pipeline = build_ghidra_analyzer_pipeline(mock_llm)
            
            # Run the pipeline with the query
            result = pipeline.run("List all functions in the binary")
            
            # Check that the response contains all function names
            for func in MOCK_FUNCTIONS:
                self.assertIn(func["name"], result)
    
    @unittest.skip("Requires full ADK setup with LiteLLM")
    def test_explain_function(self):
        """Test if the agent can explain what a function does"""
        from src.adk_agents.ghidra_analyzer.agents import build_ghidra_analyzer_pipeline
        
        # Mock the tools and agent response
        with patch('src.adk_tools.ghidra_mcp') as mock_ghidra:
            mock_tools = setup_mock_tool_calls()
            for name, func in mock_tools.items():
                setattr(mock_ghidra, name, func)
            
            # Set up the agent pipeline with mock LLM
            mock_llm = MagicMock()
            mock_llm.generate.return_value = (
                "The validate_user function checks if the provided username and password match "
                "the hardcoded credentials 'admin' and 'password123'. If they match, it returns true, "
                "otherwise it returns false. This is a basic authentication function with hardcoded credentials."
            )
            
            pipeline = build_ghidra_analyzer_pipeline(mock_llm)
            
            # Run the pipeline with the query
            result = pipeline.run("What does the validate_user function do?")
            
            # Check that the response contains key information about the function
            self.assertIn("validate_user", result)
            self.assertIn("credentials", result.lower())
            self.assertIn("authentication", result.lower())
    
    @unittest.skip("Requires full ADK setup with LiteLLM")
    def test_recursive_traversal(self):
        """Test if the agent can recursively traverse functions from the entry point"""
        from src.adk_agents.ghidra_analyzer.agents import build_ghidra_analyzer_pipeline
        
        # Mock the tools and agent response
        with patch('src.adk_tools.ghidra_mcp') as mock_ghidra:
            mock_tools = setup_mock_tool_calls()
            for name, func in mock_tools.items():
                setattr(mock_ghidra, name, func)
            
            # Set up the agent pipeline with mock LLM
            mock_llm = MagicMock()
            mock_llm.generate.return_value = (
                "Program behavior analysis:\n"
                "1. The program starts at main and checks if command line arguments are provided.\n"
                "2. It reads a file specified by the first argument using read_file.\n"
                "3. It validates user credentials with validate_user (hardcoded as 'admin'/'password123').\n"
                "4. If authentication succeeds, it processes the file content with process_input.\n"
                "5. The process_input function counts newline characters in the input.\n"
                "6. The program prints the result and frees memory before exiting."
            )
            
            pipeline = build_ghidra_analyzer_pipeline(mock_llm)
            
            # Run the pipeline with the query
            result = pipeline.run("Recursively traverse the functions from main and describe the programmatic behavior")
            
            # Check that the response contains information about the program flow
            self.assertIn("main", result)
            self.assertIn("read_file", result)
            self.assertIn("validate_user", result)
            self.assertIn("process_input", result)
    
    @unittest.skip("Requires full ADK setup with LiteLLM")
    def test_rename_function(self):
        """Test if the agent can rename a function based on its behavior"""
        from src.adk_agents.ghidra_analyzer.agents import build_ghidra_analyzer_pipeline
        
        # Mock the tools and agent response
        with patch('src.adk_tools.ghidra_mcp') as mock_ghidra:
            mock_tools = setup_mock_tool_calls()
            for name, func in mock_tools.items():
                setattr(mock_ghidra, name, func)
            
            # Set up the agent pipeline with mock LLM
            mock_llm = MagicMock()
            mock_llm.generate.return_value = (
                "Based on the decompiled code, I've renamed the function from 'validate_user' to "
                "'authenticate_credentials' as it more accurately describes its purpose of checking "
                "username and password against hardcoded values."
            )
            
            pipeline = build_ghidra_analyzer_pipeline(mock_llm)
            
            # Run the pipeline with the query
            result = pipeline.run("Rename the validate_user function based on its behavior")
            
            # Check that the response contains information about the renaming
            self.assertIn("validate_user", result)
            self.assertIn("rename", result.lower())
            self.assertIn("credential", result.lower())

if __name__ == '__main__':
    unittest.main() 