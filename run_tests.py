#!/usr/bin/env python3
"""
Test runner script for Red Team AI Agent.

This script runs the test suite and provides helpful output for development.
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run the full test suite."""
    print("🧪 Running Red Team AI Agent Test Suite")
    print("=" * 50)
    
    # Change to project directory
    project_root = Path(__file__).parent
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=redteam",
        "--cov-report=term-missing",
        "--verbose"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
        
        return result.returncode
        
    except FileNotFoundError:
        print("❌ pytest not found. Install with: poetry install")
        return 1

def run_quick_test():
    """Run a quick smoke test."""
    print("🚀 Running Quick Smoke Test")
    print("-" * 30)
    
    try:
        # Import core components to verify they load
        from redteam.attacks.prompt_injection.direct_injection import DirectInjectionAttack
        from redteam.targets.base import MockTarget
        from redteam.core.campaign import Campaign
        
        print("✅ Core modules import successfully")
        
        # Create basic objects
        attack = DirectInjectionAttack()
        target = MockTarget("test", "test")
        
        print("✅ Basic object creation works")
        print("🎉 Smoke test passed!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        exit_code = run_quick_test()
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)