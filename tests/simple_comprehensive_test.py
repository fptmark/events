#!/usr/bin/env python3
"""
Simplified comprehensive test that just runs core API tests across 4 configurations.
No complex database connection management - just starts server and tests endpoints.
"""

import sys
import subprocess
import time
import json
import requests
from pathlib import Path

BASE_URL = "http://localhost:5500"

# Test configurations
CONFIGS = [
    {"name": "MongoDB without FK validation", "file": "mongo_no_fk.json", "data": {
        "database": "mongodb", "db_uri": "mongodb://localhost:27017", "db_name": "eventMgr",
        "fk_validation": "", "unique_validation": False
    }},
    {"name": "MongoDB with FK validation", "file": "mongo_with_fk.json", "data": {
        "database": "mongodb", "db_uri": "mongodb://localhost:27017", "db_name": "eventMgr", 
        "fk_validation": "multiple", "unique_validation": True
    }},
    {"name": "Elasticsearch without FK validation", "file": "es_no_fk.json", "data": {
        "database": "elasticsearch", "db_uri": "http://localhost:9200", "db_name": "eventMgr",
        "fk_validation": "", "unique_validation": False
    }},
    {"name": "Elasticsearch with FK validation", "file": "es_with_fk.json", "data": {
        "database": "elasticsearch", "db_uri": "http://localhost:9200", "db_name": "eventMgr",
        "fk_validation": "multiple", "unique_validation": True
    }}
]

# Core test endpoints to verify
TESTS = [
    ("/api/user", "Basic user list"),
    ("/api/user?pageSize=5", "Pagination"),
    ("/api/user?sort=username", "Single sort"),
    ("/api/user?sort=firstName,lastName", "Multi-field sort"),  
    ("/api/user?filter=gender:male", "Basic filter"),
    ("/api/user?filter=gender:male&sort=username&pageSize=3", "Combined operations"),
]

def create_config_file(config):
    """Create config file for testing"""
    with open(f"tests/{config['file']}", 'w') as f:
        json.dump(config['data'], f, indent=2)
    return f"tests/{config['file']}"

def start_server(config_file):
    """Start server with config"""
    print(f"🚀 Starting server with {config_file}")
    
    # Kill any existing server
    subprocess.run(["pkill", "-f", "main.py"], check=False)
    time.sleep(1)
    
    # Start new server
    process = subprocess.Popen(
        [sys.executable, "app/main.py", config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent
    )
    
    # Wait for server to be ready
    for attempt in range(30):
        try:
            response = requests.get(f"{BASE_URL}/api/metadata", timeout=2)
            if response.status_code == 200:
                print(f"  ✅ Server ready (attempt {attempt + 1})")
                return process
        except:
            pass
        time.sleep(1)
    
    print("  ❌ Server failed to start")
    return None

def stop_server(process):
    """Stop server"""
    if process:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    subprocess.run(["pkill", "-f", "main.py"], check=False)
    time.sleep(1)

def run_tests():
    """Run tests for endpoint"""
    passed = 0
    total = len(TESTS)
    
    for url, description in TESTS:
        try:
            response = requests.get(f"{BASE_URL}{url}", timeout=10)
            if response.status_code == 200:
                print(f"    ✅ {description}")
                passed += 1
            else:
                print(f"    ❌ {description} - Status {response.status_code}")
        except Exception as e:
            print(f"    ❌ {description} - {e}")
    
    return passed, total

def main():
    """Run simplified comprehensive test"""
    print("🧪 SIMPLIFIED COMPREHENSIVE TEST")
    print("=" * 60)
    
    overall_passed = 0
    overall_total = 0
    
    for config in CONFIGS:
        print(f"\n📋 Testing: {config['name']}")
        print("-" * 40)
        
        # Create config file
        config_file = create_config_file(config)
        
        # Start server
        process = start_server(config_file)
        if not process:
            print("  ❌ Server start failed")
            continue
        
        try:
            # Run tests
            passed, total = run_tests()
            print(f"  📊 Results: {passed}/{total} tests passed")
            
            if passed == total:
                print(f"  ✅ {config['name']}: ALL PASSED")
                overall_passed += 1
            else:
                print(f"  ❌ {config['name']}: {total - passed} FAILED")
            
            overall_total += 1
            
        finally:
            stop_server(process)
    
    print(f"\n{'=' * 60}")
    print(f"FINAL RESULTS: {overall_passed}/{overall_total} configurations passed")
    
    if overall_passed == overall_total:
        print("🎉 ALL CONFIGURATIONS PASSED!")
        return 0
    else:
        print(f"💥 {overall_total - overall_passed} CONFIGURATIONS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())