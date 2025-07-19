#!/usr/bin/env python3
"""
Check if calculate_overall_qa_score is properly defined in qa.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "="*80)
print("🔍 CHECKING QA.PY FUNCTIONS")
print("="*80 + "\n")

# Read the qa.py file
qa_file = project_root / "workflow" / "nodes" / "qa.py"

if qa_file.exists():
    with open(qa_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"✅ Found qa.py file ({len(content)} chars)")
    
    # Check for function definitions
    functions_to_check = [
        "calculate_overall_qa_score",
        "assemble_final_report",
        "parse_json_with_fixes",
        "qa_node"
    ]
    
    for func_name in functions_to_check:
        # Find all occurrences
        def_pattern = f"def {func_name}"
        call_pattern = f"{func_name}("
        
        def_count = content.count(def_pattern)
        call_count = content.count(call_pattern) - def_count  # Subtract definition from calls
        
        # Find line numbers
        lines = content.split('\n')
        def_lines = []
        call_lines = []
        
        for i, line in enumerate(lines, 1):
            if def_pattern in line:
                def_lines.append(i)
            elif call_pattern in line and "def " not in line:
                call_lines.append(i)
        
        print(f"\n📌 {func_name}:")
        print(f"   Defined: {def_count} time(s) at line(s): {def_lines}")
        print(f"   Called: {call_count} time(s) at line(s): {call_lines[:5]}...")  # Show first 5
        
        # Check if defined before first call
        if def_lines and call_lines:
            if min(call_lines) < min(def_lines):
                print(f"   ⚠️  WARNING: Called before definition!")
    
    # Check imports
    print("\n📌 Checking imports:")
    if "from workflow.core.validators import" in content:
        import_start = content.find("from workflow.core.validators import")
        import_end = content.find(")", import_start)
        import_section = content[import_start:import_end+1]
        print(f"   Found import: {import_section[:100]}...")
        
        if "calculate_overall_qa_score" in import_section:
            print("   ❌ ERROR: calculate_overall_qa_score is in imports but should be defined locally!")
    
else:
    print("❌ qa.py file not found!")

print("\n" + "="*80)