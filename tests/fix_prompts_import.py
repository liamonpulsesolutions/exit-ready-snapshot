#!/usr/bin/env python3
"""
Quick fix to add missing import to workflow/core/prompts.py
"""

import os
from pathlib import Path

# Find the prompts.py file
prompts_file = Path("workflow/core/prompts.py")

if prompts_file.exists():
    # Read the current content
    with open(prompts_file, 'r') as f:
        content = f.read()
    
    # Check if typing imports are present
    if "from typing import" not in content:
        # Add the import at the beginning after docstring
        lines = content.split('\n')
        
        # Find where to insert (after module docstring)
        insert_pos = 0
        in_docstring = False
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') and not in_docstring:
                in_docstring = True
            elif line.strip().endswith('"""') and in_docstring:
                insert_pos = i + 1
                break
        
        # Insert the import
        lines.insert(insert_pos, "from typing import Dict, Tuple")
        lines.insert(insert_pos + 1, "")
        
        # Write back
        with open(prompts_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Fixed imports in {prompts_file}")
        print("Added: from typing import Dict, Tuple")
    else:
        # Check if Dict is in the import
        if "Dict" not in content:
            # Find the typing import line and add Dict
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith("from typing import"):
                    # Add Dict to the import
                    if "Dict" not in line:
                        lines[i] = line.rstrip() + ", Dict"
                        if "Tuple" not in line:
                            lines[i] = lines[i] + ", Tuple"
                        break
            
            # Write back
            with open(prompts_file, 'w') as f:
                f.write('\n'.join(lines))
            
            print(f"✅ Updated imports in {prompts_file}")
        else:
            print(f"ℹ️  Imports already correct in {prompts_file}")
else:
    print(f"❌ File not found: {prompts_file}")
    print("Current directory:", os.getcwd())