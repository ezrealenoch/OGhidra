#!/usr/bin/env python3
"""
Test script to verify the connection to the GhidraMCP server.

This script attempts to connect to a running GhidraMCP server and
provides feedback on the connection status and any errors encountered.
"""

import sys
import os
import time
import argparse
import logging
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_connection(server_url, max_retries=3, retry_delay=2, timeout=10):
    """
    Test if the GhidraMCP server is accessible.
    
    Args:
        server_url: The URL of the GhidraMCP server
        max_retries: Number of connection attempts
        retry_delay: Seconds to wait between retries
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple of (bool, str) indicating success/failure and a message
    """
    logger.info(f"Testing connection to GhidraMCP server at {server_url}")
    
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                # First try a simple ping endpoint
                logger.info(f"Attempt {attempt+1}/{max_retries}: Pinging server...")
                
                try:
                    response = client.get(f"{server_url}/ping")
                    if response.status_code == 200:
                        return True, f"Successfully connected to GhidraMCP server at {server_url} (ping endpoint)"
                except httpx.RequestError:
                    logger.info("Ping endpoint not available, trying list_functions...")
                
                # If ping fails, try the list_functions endpoint which should always be available
                response = client.get(f"{server_url}/list_functions")
                
                if response.status_code == 200:
                    # Try to get the function list to confirm it's actually Ghidra
                    try:
                        functions = response.json()
                        function_count = len(functions) if isinstance(functions, list) else "unknown"
                        return True, (f"Successfully connected to GhidraMCP server at {server_url}. "
                                     f"Found {function_count} functions.")
                    except:
                        # Even if we can't parse the response, connection was successful
                        return True, f"Successfully connected to GhidraMCP server at {server_url}"
                else:
                    logger.warning(f"Server responded with status code {response.status_code}")
                    
        except httpx.ConnectError as e:
            logger.warning(f"Connection error (attempt {attempt+1}/{max_retries}): {e}")
        except httpx.TimeoutException as e:
            logger.warning(f"Connection timeout (attempt {attempt+1}/{max_retries}): {e}")
        except Exception as e:
            logger.warning(f"Unexpected error (attempt {attempt+1}/{max_retries}): {e}")
            
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    # All attempts failed
    error_message = (
        f"Failed to connect to GhidraMCP server at {server_url} after {max_retries} attempts.\n\n"
        f"Please ensure that:\n"
        f"1. Ghidra is running\n"
        f"2. The GhidraMCP plugin is installed and enabled in Ghidra\n"
        f"3. The GhidraMCP server is configured to run on {server_url}\n"
        f"4. There are no firewall restrictions blocking the connection\n"
        f"5. You can verify the port in Ghidra using Edit → Tool Options → GhidraMCP HTTP Server"
    )
    return False, error_message

def main():
    """Run the GhidraMCP connection test."""
    parser = argparse.ArgumentParser(description="Test connection to GhidraMCP server")
    parser.add_argument("--url", default="http://127.0.0.1:8080",
                        help="GhidraMCP server URL (default: http://127.0.0.1:8080)")
    parser.add_argument("--retries", type=int, default=3, 
                        help="Maximum number of connection attempts (default: 3)")
    parser.add_argument("--delay", type=int, default=2,
                        help="Delay between retries in seconds (default: 2)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Connection timeout in seconds (default: 10)")
    args = parser.parse_args()
    
    success, message = test_connection(
        args.url, 
        max_retries=args.retries,
        retry_delay=args.delay,
        timeout=args.timeout
    )
    
    if success:
        logger.info("✅ " + message)
        return 0
    else:
        logger.error("❌ " + message)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 