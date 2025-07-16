"""
Quick test to verify imports are working
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"Python path includes: {project_root}")

try:
    print("\n1. Testing workflow.state import...")
    from workflow.state import WorkflowState
    print("✅ WorkflowState imported successfully")
    
    print("\n2. Testing workflow.core.validators import...")
    from workflow.core.validators import (
        validate_scoring_consistency,
        validate_content_quality,
        scan_for_pii,
        validate_report_structure
    )
    print("✅ Validators imported successfully")
    
    print("\n3. Testing workflow.graph import...")
    from workflow.graph import process_assessment_async
    print("✅ process_assessment_async imported successfully")
    
    print("\n4. Testing workflow.core.pii_handler import...")
    from workflow.core.pii_handler import store_pii_mapping
    print("✅ store_pii_mapping imported successfully")
    
    print("\n5. Testing all workflow nodes imports...")
    from workflow.nodes.qa import qa_node
    print("✅ qa_node imported successfully")
    
    from workflow.nodes.intake import intake_node
    print("✅ intake_node imported successfully")
    
    from workflow.nodes.research import research_node
    print("✅ research_node imported successfully")
    
    from workflow.nodes.scoring import scoring_node
    print("✅ scoring_node imported successfully")
    
    from workflow.nodes.summary import summary_node
    print("✅ summary_node imported successfully")
    
    from workflow.nodes.pii_reinsertion import pii_reinsertion_node
    print("✅ pii_reinsertion_node imported successfully")
    
    print("\n✨ All imports successful! The module structure is correct.")
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print(f"   Module not found: {e.name if hasattr(e, 'name') else 'unknown'}")
    import traceback
    traceback.print_exc()