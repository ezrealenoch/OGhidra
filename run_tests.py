#!/usr/bin/env python3
"""
Test runner for OGhidra unit tests.
"""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests in the tests directory."""
    # Add the project root to path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    test_suite = loader.discover('tests', pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return non-zero exit code if tests failed
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 