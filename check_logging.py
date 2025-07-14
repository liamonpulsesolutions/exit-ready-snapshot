#!/usr/bin/env python
"""
Check if logging is configured to suppress output
"""

print("=== CHECKING LOGGING CONFIGURATION ===")

import sys
import os
import logging

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Check logging configuration
print("\nLogging configuration:")
print(f"Root logger level: {logging.getLogger().getEffectiveLevel()}")
print(f"Root logger handlers: {logging.getLogger().handlers}")

# Check if any modules are setting logging config
print("\nChecking module logging...")

# Try a simple logging test
print("\nTesting basic logging:")
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")

# Check stderr/stdout
print("\nChecking stdout/stderr:")
print(f"stdout: {sys.stdout}")
print(f"stderr: {sys.stderr}")

# Try importing and checking if there's an __init__.py issue
print("\nChecking package structure:")
src_init = os.path.join("src", "__init__.py")
nodes_init = os.path.join("src", "nodes", "__init__.py")
print(f"src/__init__.py exists: {os.path.exists(src_init)}")
print(f"src/nodes/__init__.py exists: {os.path.exists(nodes_init)}")

# Simple function test
print("\nTesting simple function execution:")

def test_function():
    print("  Inside test function")
    return "Function worked"

result = test_function()
print(f"  Result: {result}")

print("\n=== CHECK COMPLETE ===")

# Now let's try to import with verbose error handling
print("\nAttempting imports with verbose error handling...")

try:
    import src
    print("✓ src package imported")
except ImportError as e:
    print(f"✗ Cannot import src: {e}")

try:
    import src.nodes
    print("✓ src.nodes package imported")
except ImportError as e:
    print(f"✗ Cannot import src.nodes: {e}")

try:
    from src.nodes import intake_node
    print("✓ intake_node module imported")
except ImportError as e:
    print(f"✗ Cannot import intake_node: {e}")
    
    # Try direct file import
    print("\nTrying direct file import...")
    try:
        sys.path.append(os.path.join(os.getcwd(), 'src', 'nodes'))
        import intake_node
        print("✓ Direct import worked")
    except Exception as e2:
        print(f"✗ Direct import failed: {e2}")

print("\nDiagnostic complete.")