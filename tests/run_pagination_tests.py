#!/usr/bin/env python3
"""
Standalone test runner for pagination/filtering tests.

Usage:
  python tests/run_pagination_tests.py          # Run with default config  
  python tests/run_pagination_tests.py config.json  # Run with specific config
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_pagination_tests(config_file=None):
    """Run pagination/filtering tests with optional config."""
    import pytest
    
    # Set up test environment
    if config_file and Path(config_file).exists():
        print(f"📋 Using configuration: {config_file}")
        os.environ['CONFIG_FILE'] = config_file
    else:
        print("📋 Using default configuration")
    
    # Run the specific test module
    test_file = str(Path(__file__).parent / "test_pagination_filtering.py")
    
    print("🧪 Running Pagination/Filtering Tests")
    print("=" * 50)
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        test_file,
        "-v",           # Verbose output
        "-s",           # Don't capture output (show prints)
        "--tb=short",   # Short traceback format
        "--color=yes"   # Colored output
    ])
    
    if exit_code == 0:
        print("\n✅ All pagination/filtering tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_pagination_tests(config_file))