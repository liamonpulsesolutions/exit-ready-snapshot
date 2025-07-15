#!/usr/bin/env python
"""
Find where the default scoring values are coming from
"""

import sys
import os
import json
import ast
from datetime import datetime
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture output
_original_stdout = sys.stdout
_stdout_capture = StringIO()

class TeeOutput:
    def __init__(self, capture, original):
        self.capture = capture
        self.original = original
    def write(self, data):
        self.capture.write(data)
        self.original.write(data)
    def flush(self):
        self.capture.flush()
        self.original.flush()
    def isatty(self):
        return self.original.isatty() if hasattr(self.original, 'isatty') else False
    def __getattr__(self, name):
        return getattr(self.original, name)

sys.stdout = TeeOutput(_stdout_capture, _original_stdout)

print("🔍 FINDING SOURCE OF DEFAULT SCORING VALUES")
print("=" * 60)

# Search for hardcoded scores in scoring_node.py
print("\n1️⃣ Searching for hardcoded values in scoring_node.py...")

scoring_node_path = os.path.join("src", "nodes", "scoring_node.py")
if os.path.exists(scoring_node_path):
    with open(scoring_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Look for patterns that might indicate default values
    patterns_to_find = [
        "4.6",  # The score we're seeing
        "default",
        "hardcoded",
        "fallback",
        "mock",
        "dummy",
        "test_",
        "MOCK_",
        "DEFAULT_"
    ]
    
    for pattern in patterns_to_find:
        occurrences = []
        for i, line in enumerate(lines, 1):
            if pattern.lower() in line.lower():
                occurrences.append((i, line.strip()))
        
        if occurrences:
            print(f"\n   Found '{pattern}' in {len(occurrences)} places:")
            for line_num, line_content in occurrences[:3]:  # Show first 3
                print(f"      Line {line_num}: {line_content[:80]}...")
else:
    print(f"   ❌ File not found: {scoring_node_path}")

# Check if there's a mock or test version being imported
print("\n2️⃣ Checking for test/mock imports...")

import sys
for module_name, module in sys.modules.items():
    if 'scoring' in module_name and ('mock' in module_name or 'test' in module_name):
        print(f"   ⚠️  Found suspicious module: {module_name}")

# Look for fixture files
print("\n3️⃣ Searching for fixture/test data files...")

fixture_patterns = ['fixture', 'mock', 'test_data', 'default']
for root, dirs, files in os.walk('.'):
    for file in files:
        if any(pattern in file.lower() for pattern in fixture_patterns):
            if 'scoring' in file.lower() or 'score' in file.lower():
                print(f"   Found: {os.path.join(root, file)}")

# Check if scoring functions are being mocked
print("\n4️⃣ Checking if scoring functions are mocked...")

try:
    import src.agents.scoring_agent as scoring_module
    
    # Check each function
    functions_to_check = [
        'score_financial_performance',
        'score_revenue_stability',
        'score_operations_efficiency',
        'score_growth_value',
        'score_exit_readiness'
    ]
    
    for func_name in functions_to_check:
        if hasattr(scoring_module, func_name):
            func = getattr(scoring_module, func_name)
            # Check if it's a mock
            if hasattr(func, '__name__'):
                if 'mock' in func.__name__.lower() or 'test' in func.__name__.lower():
                    print(f"   ⚠️  {func_name} appears to be mocked!")
            # Check the source
            import inspect
            try:
                source = inspect.getsource(func)
                if len(source) < 200:  # Suspiciously short
                    print(f"   ⚠️  {func_name} is suspiciously short ({len(source)} chars)")
                    print(f"      First line: {source.split(chr(10))[0]}")
            except:
                print(f"   ❌ Cannot inspect {func_name}")

except Exception as e:
    print(f"   ❌ Error checking functions: {e}")

# Look for environment variables that might enable test mode
print("\n5️⃣ Checking environment variables...")

import os
test_env_vars = [var for var in os.environ.keys() if 'TEST' in var or 'MOCK' in var or 'DEBUG' in var]
if test_env_vars:
    print(f"   Found {len(test_env_vars)} test-related environment variables:")
    for var in test_env_vars:
        print(f"      {var} = {os.environ[var]}")
else:
    print("   No test-related environment variables found")

# Check the actual scoring_node source for where results come from
print("\n6️⃣ Analyzing scoring_node result generation...")

if os.path.exists(scoring_node_path):
    # Look for where scoring_result is created
    for i, line in enumerate(lines, 1):
        if 'scoring_result' in line and '=' in line and '{' in line:
            print(f"\n   Found scoring_result assignment at line {i}:")
            # Show context
            start = max(0, i-3)
            end = min(len(lines), i+10)
            for j in range(start, end):
                marker = ">>>" if j == i-1 else "   "
                print(f"   {marker} {lines[j]}")
            break

# Save findings
output = {
    "timestamp": datetime.now().isoformat(),
    "found_hardcoded_values": {},
    "suspicious_modules": [],
    "test_env_vars": test_env_vars if 'test_env_vars' in locals() else [],
    "terminal_output": _stdout_capture.getvalue().split('\n')
}

filename = f"output_find_defaults_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Restore stdout before saving
sys.stdout = _original_stdout

with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Findings saved to: {filename}")
print("\n" + "=" * 60)
print("SEARCH COMPLETE")