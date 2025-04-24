#!/usr/bin/env python3
"""
Runs test cases for the Ghidra Analyzer agent.
"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

if __name__ == "__main__":
    from tests import TestGhidraAnalyzer
    
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGhidraAnalyzer)
    
    # Run the tests
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Return non-zero exit code if tests failed
    sys.exit(not result.wasSuccessful())