#!/usr/bin/env python3
"""
Quick script to run the existing E2E test and check results.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "="*80)
print("🚀 RUNNING E2E TEST WITH FIXES")
print("="*80 + "\n")

print("📝 Summary of fixes applied:")
print("   ✅ research.py - Ensures proper dict structure")
print("   ✅ scoring.py - Fixed industry extraction and response counting")
print("   ✅ summary.py - Added null checks for missing data")
print("\n")

# Run the E2E test
test_file = project_root / "tests" / "test_e2e_enhanced_workflow.py"

print(f"🧪 Executing: {test_file.name}")
print("-" * 80)

try:
    # Run the test
    result = subprocess.run(
        [sys.executable, str(test_file)],
        capture_output=False,  # Let output show in real-time
        text=True
    )
    
    print("\n" + "-" * 80)
    
    if result.returncode == 0:
        print("✅ Test execution completed successfully!")
    else:
        print(f"❌ Test failed with return code: {result.returncode}")
    
    # Look for the most recent output file
    import glob
    output_files = sorted(glob.glob("output_test_e2e_enhanced_*.json"), reverse=True)
    
    if output_files:
        latest_file = output_files[0]
        print(f"\n📊 Analyzing results from: {latest_file}")
        
        # Load and check results
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        # Extract key metrics
        assertions = data.get("assertions", [])
        total = len(assertions)
        passed = sum(1 for a in assertions if a["passed"])
        failed = total - passed
        
        print(f"\n📈 Test Results:")
        print(f"   Total Assertions: {total}")
        print(f"   Passed: {passed} ({'✅' if passed == total else '⚠️'})")
        print(f"   Failed: {failed} ({'✅' if failed == 0 else '❌'})")
        
        if failed > 0:
            print(f"\n❌ Failed Assertions:")
            for a in assertions:
                if not a["passed"]:
                    print(f"   - {a['description']}")
                    if a.get("details"):
                        print(f"     Details: {a['details']}")
        
        # Check for errors
        errors = data.get("errors", [])
        if errors:
            print(f"\n❌ Errors Encountered: {len(errors)}")
            for err in errors:
                print(f"   - {err.get('error', err)}")
        
        # Check execution time
        exec_time = data.get("results", {}).get("execution_time")
        if exec_time:
            print(f"\n⏱️  Execution Time: {exec_time:.1f} seconds")
        
        # Check if scoring worked
        workflow_result = data.get("results", {}).get("workflow_result", {})
        if workflow_result:
            scores = workflow_result.get("scores", {})
            if scores:
                print(f"\n🎯 Scoring Results:")
                print(f"   Overall Score: {scores.get('overall', 'N/A')}/10")
                print(f"   Categories scored: {len([k for k in scores if k != 'overall'])}")
            else:
                print("\n❌ No scores generated!")
        
        print(f"\n💡 Next Steps:")
        if passed == total and not errors:
            print("   ✨ All tests passed! The pipeline is working correctly.")
            print("   🚀 Ready to update the remediation checklist to 100%!")
        else:
            print("   🔍 Review the failed assertions and errors above")
            print("   🛠️  Additional fixes may be needed")
            
    else:
        print("\n⚠️  No output file found!")
    
except Exception as e:
    print(f"\n❌ Error running test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)