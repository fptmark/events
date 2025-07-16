#!/usr/bin/env python3
"""
Simple test runner that actually works.
"""

import sys
import os
import subprocess
import time
import json
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def kill_server():
    """Kill any server on port 5500"""
    try:
        subprocess.run(["pkill", "-f", "app/main.py"], check=False)
        subprocess.run(["lsof", "-ti:5500"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        result = subprocess.run(["lsof", "-ti:5500"], capture_output=True, text=True, check=False)
        if result.stdout.strip():
            for pid in result.stdout.strip().split('\n'):
                if pid.strip():
                    subprocess.run(["kill", "-9", pid.strip()], check=False)
    except:
        pass
    time.sleep(1)

def start_server(config_file):
    """Start server with config file"""
    print(f"🚀 Starting server with {config_file}")
    
    # Kill any existing server
    kill_server()
    
    # Start server in background
    env = os.environ.copy()
    env['CONFIG_FILE'] = config_file
    
    server_process = subprocess.Popen(
        [sys.executable, "app/main.py"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    # Wait for server to be ready
    import requests
    for i in range(30):
        try:
            response = requests.get("http://localhost:5500/api/metadata", timeout=1)
            if response.status_code == 200:
                print(f"  ✅ Server ready (attempt {i+1})")
                return server_process
        except:
            pass
        time.sleep(1)
    
    print("  ❌ Server failed to start")
    return None

def run_test(config_file, description):
    """Run test with config file"""
    print(f"\n{'='*60}")
    print(f"TESTING: {description}")
    print('='*60)
    
    # Start server
    server_process = start_server(config_file)
    if not server_process:
        return False
    
    try:
        # Run test
        print("🧪 Running tests...")
        result = subprocess.run(
            [sys.executable, "tests/test_user_validation.py", config_file],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Parse results
        passed = 0
        total = 0
        for line in result.stdout.split('\n'):
            if "Total tests:" in line:
                total = int(line.split(":")[1].strip())
            elif "Passed:" in line:
                passed = int(line.split(":")[1].strip())
        
        success = result.returncode == 0
        print(f"Result: {passed}/{total} tests passed")
        
        if not success:
            print("STDERR:", result.stderr)
        
        return success
        
    finally:
        # Kill server
        kill_server()

def main():
    """Main function"""
    print("🧪 SIMPLE TEST RUNNER")
    print("=" * 60)
    
    # Create config files
    configs = {
        "temp_mongo_none.json": {
            "database": "mongodb",
            "db_uri": "mongodb://localhost:27017",
            "db_name": "eventMgr",
            "get_validation": "",
            "unique_validation": False
        },
        "temp_mongo_validation.json": {
            "database": "mongodb",
            "db_uri": "mongodb://localhost:27017",
            "db_name": "eventMgr",
            "get_validation": "get_all",
            "unique_validation": True
        },
        "temp_es_none.json": {
            "database": "elasticsearch",
            "db_uri": "http://localhost:9200",
            "db_name": "eventMgr",
            "get_validation": "",
            "unique_validation": False
        },
        "temp_es_validation.json": {
            "database": "elasticsearch",
            "db_uri": "http://localhost:9200",
            "db_name": "eventMgr",
            "get_validation": "get_all",
            "unique_validation": True
        }
    }
    
    # Create config files
    for filename, config in configs.items():
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
    
    # Test configurations
    tests = [
        ("temp_mongo_none.json", "MongoDB without validation"),
        ("temp_mongo_validation.json", "MongoDB with validation"),
        ("temp_es_none.json", "Elasticsearch without validation"),
        ("temp_es_validation.json", "Elasticsearch with validation")
    ]
    
    results = []
    
    # Run tests
    for config_file, description in tests:
        success = run_test(config_file, description)
        results.append((description, success))
        
        if success:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    passed_count = sum(1 for _, success in results if success)
    
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {description}")
    
    print(f"\nResult: {passed_count}/{len(results)} configurations passed")
    
    # Cleanup
    for filename in configs.keys():
        try:
            os.remove(filename)
        except:
            pass
    
    kill_server()
    
    if passed_count == len(results):
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("💥 SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())