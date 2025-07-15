#!/usr/bin/env python3
"""
Check all dependencies and environment setup for intake node testing.
"""

import os
import sys
import importlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_import(module_path, item_name=None):
    """Try to import a module and optionally a specific item"""
    try:
        module = importlib.import_module(module_path)
        if item_name:
            item = getattr(module, item_name, None)
            if item:
                print(f"✅ {module_path}.{item_name}")
                return True
            else:
                print(f"❌ {module_path}.{item_name} - Item not found in module")
                return False
        else:
            print(f"✅ {module_path}")
            return True
    except ImportError as e:
        print(f"❌ {module_path} - {str(e)}")
        return False
    except Exception as e:
        print(f"❌ {module_path} - Unexpected error: {str(e)}")
        return False

def check_file_exists(filepath):
    """Check if a file exists"""
    full_path = project_root / filepath
    exists = full_path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {filepath}")
    return exists

def main():
    print("🔍 DEPENDENCY CHECK FOR INTAKE NODE\n")
    
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[0]}")
    print(f"Current directory: {os.getcwd()}\n")
    
    # Check file structure
    print("📁 Checking file structure:")
    files_ok = all([
        check_file_exists("workflow/__init__.py"),
        check_file_exists("workflow/state.py"),
        check_file_exists("workflow/graph.py"),
        check_file_exists("workflow/nodes/__init__.py"),
        check_file_exists("workflow/nodes/intake.py"),
        check_file_exists("workflow/core/__init__.py"),
        check_file_exists("workflow/core/validators.py"),
        check_file_exists("workflow/core/pii_handler.py"),
    ])
    
    print("\n📦 Checking core imports:")
    core_ok = all([
        check_import("workflow.state", "WorkflowState"),
        check_import("workflow.nodes.intake", "intake_node"),
        check_import("workflow.core.validators", "validate_form_data"),
        check_import("workflow.core.pii_handler", "anonymize_form_data"),
    ])
    
    print("\n🛠️ Checking tools and utilities:")
    tools_ok = all([
        check_import("src.tools.google_sheets", "GoogleSheetsLogger"),
        check_import("src.utils.pii_storage", "store_pii_mapping"),
    ])
    
    print("\n📚 Checking external libraries:")
    libs_ok = all([
        check_import("langgraph.graph", "StateGraph"),
        check_import("dotenv", "load_dotenv"),
        check_import("openai", "OpenAI"),
    ])
    
    # Check environment variables
    print("\n🔐 Checking environment variables:")
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = [
        "OPENAI_API_KEY",
        "PERPLEXITY_API_KEY",
        "GOOGLE_SHEETS_CREDENTIALS_PATH",  # Fixed: was looking for wrong env var name
        "CRM_SPREADSHEET_ID",
        "RESPONSES_SPREADSHEET_ID"
    ]
    
    env_ok = True
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} (length: {len(value)})")
        else:
            print(f"❌ {var} - Not set")
            env_ok = False
    
    # Summary
    print("\n" + "="*50)
    print("📊 SUMMARY:")
    print("="*50)
    
    all_ok = files_ok and core_ok and tools_ok and libs_ok and env_ok
    
    print(f"File structure: {'✅ OK' if files_ok else '❌ FAILED'}")
    print(f"Core imports: {'✅ OK' if core_ok else '❌ FAILED'}")
    print(f"Tools/utilities: {'✅ OK' if tools_ok else '❌ FAILED'}")
    print(f"External libraries: {'✅ OK' if libs_ok else '❌ FAILED'}")
    print(f"Environment variables: {'✅ OK' if env_ok else '❌ FAILED'}")
    
    if all_ok:
        print("\n✅ ALL CHECKS PASSED! Ready to test intake node.")
    else:
        print("\n❌ Some checks failed. Fix the issues above before testing.")
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)