#!/usr/bin/env python3
"""
Main entry point for the Ollama-GhidraMCP Bridge application.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Import after loading environment variables
from src.bridge import main

if __name__ == "__main__":
    sys.exit(main()) 