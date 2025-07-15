#!/usr/bin/env python
"""
Verify that the scoring node fix has been applied
"""

import sys
import os
import importlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Verifying Scoring Node Fix")
print("=" * 60)

# Force reload of the module to avoid caching
print("\n1️⃣ Force reloading scoring_node module...")
if 'src.nodes.scoring_node' in sys.modules:
    del sys.modules['src.nodes.scoring_node']
if 'src.agents.scoring_agent' in sys.modules:
    del sys.modules['src.agents.scoring_agent']

# Now import fresh
from src.nodes.scoring_node import scoring_node
import inspect

print("✅ Module reloaded")

# Check if the fix is applied by looking for specific markers
print("\n2️⃣ Checking if fix is applied...")
source = inspect.getsource(scoring_node)

# Look for markers that indicate the fixed version
fix_markers = [
    "time.time()",  # Fixed version uses time.time()
    "logger.info(f\"Calling score_financial_performance...\")",  # Fixed version has this log
    "# Manually calculates the overall score",  # Comment from fixed version
    "execution_time = time.time() - start_time"  # Fixed version calculates execution time
]

found_markers = []
missing_markers = []

for marker in fix_markers:
    if marker in source:
        found_markers.append(marker)
    else:
        missing_markers.append(marker)

print(f"\nFound {len(found_markers)}/{len(fix_markers)} fix markers:")
for marker in found_markers:
    print(f"  ✅ {marker}")
for marker in missing_markers:
    print(f"  ❌ {marker}")

# Check if it's still using the old tool-based approach
print("\n3️⃣ Checking for old implementation markers...")
old_markers = [
    "aggregate_final_scores._run",  # Old version uses tools
    "calculate_focus_areas._run",  # Old version uses tools
    "parse aggregation result"  # Old version parses tool output
]

old_found = []
for marker in old_markers:
    if marker in source:
        old_found.append(marker)

if old_found:
    print(f"⚠️  WARNING: Found {len(old_found)} old implementation markers:")
    for marker in old_found:
        print(f"  - {marker}")
else:
    print("✅ No old implementation markers found")

# Final verdict
print("\n" + "=" * 60)
print("VERDICT:")
if len(found_markers) >= 3 and not old_found:
    print("✅ The scoring node appears to have the fix applied!")
    print("   The node should now call scoring functions directly.")
else:
    print("❌ The scoring node does NOT have the fix applied!")
    print("   Please ensure the fixed code is saved to src/nodes/scoring_node.py")
    print("\nTo apply the fix:")
    print("1. Copy the fixed scoring_node.py code from the artifact")
    print("2. Replace the entire contents of src/nodes/scoring_node.py")
    print("3. Save the file")
    print("4. Run this verification again")

print("=" * 60)