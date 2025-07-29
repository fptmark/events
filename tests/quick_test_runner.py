#!/usr/bin/env python3
"""
Quick test runner - assumes server is already running
"""
import subprocess
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_validation_configs():
    """Create validation config files"""
    configs = {
        "mongo_validation.json": {
            "database": "mongodb",
            "db_uri": "mongodb://localhost:27017",
            "db_name": "eventMgr", 
            "fk_validation": "multiple",
            "unique_validation": True
        },
        "es_validation.json": {
            "database": "elasticsearch",
            "db_uri": "http://localhost:9200", 
            "db_name": "eventMgr",
            "fk_validation": "multiple",
            "unique_validation": True
        }
    }
    
    for filename, config in configs.items():
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Created {filename}")

def run_single_test(config_file):
    """Run test with specific config"""
    print(f"\n{'='*60}")
    print(f"Testing with {config_file}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_user_validation.py", config_file],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("🧪 Quick Test Runner")
    print("Make sure server is running on port 5500")
    print()
    
    # Create validation configs
    create_validation_configs()
    
    # Test configurations
    configs = [
        ("mongo.json", "MongoDB without validation"),
        ("mongo_validation.json", "MongoDB with validation"),
        ("es.json", "Elasticsearch without validation"),
        ("es_validation.json", "Elasticsearch with validation")
    ]
    
    results = []
    
    for config_file, description in configs:
        print(f"\n🔍 {description}")
        print(f"Config: {config_file}")
        
        # Check if config exists
        if not Path(config_file).exists():
            print(f"❌ Config file {config_file} not found")
            results.append((description, False))
            continue
        
        success = run_single_test(config_file)
        results.append((description, success))
        
        if success:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {description}")
    
    print(f"\nOverall: {passed}/{total} configurations passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("💥 SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())