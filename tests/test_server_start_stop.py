#!/usr/bin/env python3
"""
Simple test to start and stop server as background process.
"""

import sys
import os
import subprocess
import time
import signal
from pathlib import Path

def test_server_lifecycle():
    """Test starting and stopping server"""
    print("🧪 Testing server start/stop")
    
    # Kill any existing server
    print("🔪 Killing existing servers...")
    subprocess.run(["pkill", "-f", "main.py"], check=False)
    time.sleep(1)
    
    # Create temporary config file
    temp_config = "temp_test_config.json"
    config_data = {
        "database": "mongodb",
        "db_uri": "mongodb://localhost:27017",
        "db_name": "eventMgr",
        "get_validation": "",
        "unique_validation": False
    }
    
    print("📝 Creating temporary config...")
    import json
    with open(temp_config, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    # Start server in background - EXACTLY like the command line
    print("🚀 Starting server...")
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    
    server = subprocess.Popen(
        [sys.executable, "app/main.py", temp_config],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent.parent,  # Run from project root
        env=env
    )
    
    print(f"  Server PID: {server.pid}")
    
    # Wait a bit
    time.sleep(5)
    
    # Check if server is running
    if server.poll() is None:
        print("  ✅ Server is running")
    else:
        print("  ❌ Server died")
        stdout, stderr = server.communicate()
        print("📋 STDOUT:")
        print(stdout)
        print("\n📋 STDERR:")
        print(stderr)
        print(f"\n💀 Exit code: {server.returncode}")
        return False
    
    # Test server response
    try:
        import requests
        response = requests.get("http://localhost:5500/api/metadata", timeout=5)
        print(f"  ✅ Server responds: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Server not responding: {e}")
    
    # Stop server
    print("🛑 Stopping server...")
    server.terminate()
    
    # Wait for it to stop
    try:
        server.wait(timeout=5)
        print("  ✅ Server stopped gracefully")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Server didn't stop, killing...")
        server.kill()
        server.wait()
        print("  ✅ Server killed")
    
    # Clean up temp config file
    try:
        os.remove(temp_config)
        print("🧹 Cleaned up temp config")
    except:
        pass
    
    return True

def run_comprehensive_tests():
    """Run all database and validation combinations"""
    print("🧪 COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    # Test configurations
    test_configs = [
        {
            "name": "MongoDB without validation",
            "database": "mongodb",
            "db_uri": "mongodb://localhost:27017",
            "db_name": "eventMgr",
            "get_validation": "",
            "unique_validation": False
        },
        {
            "name": "MongoDB with validation",
            "database": "mongodb",
            "db_uri": "mongodb://localhost:27017",
            "db_name": "eventMgr",
            "get_validation": "get_all",
            "unique_validation": True
        },
        {
            "name": "Elasticsearch without validation",
            "database": "elasticsearch",
            "db_uri": "http://localhost:9200",
            "db_name": "eventMgr",
            "get_validation": "",
            "unique_validation": False
        },
        {
            "name": "Elasticsearch with validation",
            "database": "elasticsearch",
            "db_uri": "http://localhost:9200",
            "db_name": "eventMgr",
            "get_validation": "get_all",
            "unique_validation": True
        }
    ]
    
    results = []
    temp_config = "temp_test_config.json"
    
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"TESTING: {config['name']}")
        print('='*80)
        
        try:
            # Kill any existing server
            print("🔪 Killing existing servers...")
            subprocess.run(["pkill", "-f", "main.py"], check=False)
            time.sleep(1)
            
            # Create config file for this test
            print("📝 Creating config...")
            import json
            with open(temp_config, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Start server
            print("🚀 Starting server...")
            env = os.environ.copy()
            env['PYTHONPATH'] = '.'
            
            server = subprocess.Popen(
                [sys.executable, "app/main.py", temp_config],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=Path(__file__).parent.parent,
                env=env
            )
            
            # Wait for server to start
            server_started = False
            for i in range(30):
                try:
                    import requests
                    response = requests.get("http://localhost:5500/api/metadata", timeout=1)
                    if response.status_code == 200:
                        print(f"  ✅ Server started (attempt {i+1})")
                        server_started = True
                        break
                except:
                    pass
                time.sleep(1)
            
            if not server_started:
                print("  ❌ Server failed to start")
                results.append((config['name'], False, 0, 0, 0))
                continue
            
            # Run tests
            print("🧪 Running tests...")
            result = subprocess.run(
                [sys.executable, "tests/test_user_validation.py", temp_config],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse results
            passed = 0
            failed = 0
            total = 0
            
            for line in result.stdout.split('\n'):
                if "Total tests:" in line:
                    total = int(line.split(":")[1].strip())
                elif "Passed:" in line:
                    passed = int(line.split(":")[1].strip())
                elif "Failed:" in line:
                    failed = int(line.split(":")[1].strip())
            
            success = result.returncode == 0
            results.append((config['name'], success, passed, failed, total))
            
            if success:
                print(f"✅ {config['name']}: {passed}/{total} tests passed")
            else:
                print(f"❌ {config['name']}: {passed}/{total} tests passed (FAILED)")
                
        except Exception as e:
            print(f"❌ {config['name']}: ERROR - {e}")
            results.append((config['name'], False, 0, 0, 0))
            
        finally:
            # Stop server
            try:
                server.terminate()
                server.wait(timeout=5)
            except:
                subprocess.run(["pkill", "-f", "main.py"], check=False)
            
            # Clean up temp config
            try:
                os.remove(temp_config)
            except:
                pass
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print('='*80)
    
    successful_configs = sum(1 for _, success, _, _, _ in results if success)
    total_passed = sum(passed for _, _, passed, _, _ in results)
    total_tests = sum(total for _, _, _, _, total in results)
    
    print(f"Configurations: {successful_configs}/{len(results)} passed")
    print(f"Total tests: {total_passed}/{total_tests} passed")
    print()
    
    for name, success, passed, failed, total in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}: {passed}/{total}")
    
    if successful_configs == len(results):
        print("\n🎉 ALL CONFIGURATIONS PASSED!")
        return True
    else:
        print("\n💥 SOME CONFIGURATIONS FAILED!")
        return False

def run_noop_process_tests():
    """Run no-op process management tests for both databases"""
    print("🧪 PROCESS MANAGEMENT NOOP TESTS")
    print("=" * 80)
    print("Testing server start/stop without running actual tests")
    
    # Test configurations
    configs = [
        ("MongoDB", {
            "database": "mongodb",
            "db_uri": "mongodb://localhost:27017",
            "db_name": "eventMgr",
            "get_validation": "",
            "unique_validation": False
        }),
        ("Elasticsearch", {
            "database": "elasticsearch", 
            "db_uri": "http://localhost:9200",
            "db_name": "eventMgr",
            "get_validation": "",
            "unique_validation": False
        })
    ]
    
    results = {}
    temp_config = "temp_noop_config.json"
    
    for name, config in configs:
        print(f"\n{'='*60}")
        print(f"NOOP TEST: {name}")
        print('='*60)
        
        try:
            # Step 1: Kill existing servers
            print("🔪 Killing existing servers...")
            subprocess.run(["pkill", "-f", "main.py"], check=False)
            time.sleep(2)
            
            # Step 2: Create config file
            print("📝 Creating config...")
            import json
            with open(temp_config, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Step 3: Start server
            print("🚀 Starting server...")
            env = os.environ.copy()
            env['PYTHONPATH'] = '.'
            
            server = subprocess.Popen(
                [sys.executable, "app/main.py", temp_config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path(__file__).parent.parent,
                env=env
            )
            
            print(f"  Server PID: {server.pid}")
            
            # Step 4: Wait for server to start
            server_started = False
            startup_time = time.time()
            
            for attempt in range(15):
                try:
                    import requests
                    response = requests.get("http://localhost:5500/api/metadata", timeout=2)
                    if response.status_code == 200:
                        elapsed = time.time() - startup_time
                        print(f"  ✅ Server started in {elapsed:.1f}s (attempt {attempt+1})")
                        server_started = True
                        break
                except Exception as e:
                    if attempt < 3:  # Only show first few attempts
                        print(f"  ⏳ Attempt {attempt+1}: {e}")
                time.sleep(1)
            
            if not server_started:
                print("  ❌ Server failed to start")
                stdout, stderr = server.communicate(timeout=5)
                print("📋 STDOUT:")
                print(stdout)
                print("\n📋 STDERR:")
                print(stderr)
                results[name] = False
                continue
            
            # Step 5: Test basic connectivity (no actual tests)
            print("🔗 Testing basic connectivity...")
            try:
                response = requests.get("http://localhost:5500/api/user", timeout=5)
                print(f"  ✅ User endpoint responds: {response.status_code}")
                
                # Test with view parameter (the problematic one)
                view_url = "http://localhost:5500/api/user?view=%7b%22account%22%3a%5b%22createdat%22%5d%7d"
                print("  🔍 Testing view endpoint (known to hang in tests)...")
                response = requests.get(view_url, timeout=15)  # Longer timeout for view
                print(f"  ✅ View endpoint responds: {response.status_code}")
                
            except Exception as e:
                print(f"  ❌ Connectivity test failed: {e}")
                results[name] = False
                continue
            
            # Step 6: Test graceful shutdown
            print("🛑 Testing graceful shutdown...")
            shutdown_time = time.time()
            
            server.terminate()
            try:
                server.wait(timeout=10)
                elapsed = time.time() - shutdown_time
                print(f"  ✅ Server stopped gracefully in {elapsed:.1f}s")
                results[name] = True
            except subprocess.TimeoutExpired:
                print("  ⚠️  Server didn't stop gracefully, killing...")
                server.kill()
                server.wait()
                print("  ⚠️  Server killed (not graceful)")
                results[name] = False
            
        except Exception as e:
            print(f"❌ Process management error: {e}")
            results[name] = False
            
        finally:
            # Cleanup
            try:
                if 'server' in locals():
                    server.kill()
                    server.wait()
            except:
                pass
            
            try:
                os.remove(temp_config)
                print("🧹 Cleaned up temp config")
            except:
                pass
    
    # Summary
    print(f"\n{'='*80}")
    print("NOOP TEST SUMMARY")
    print('='*80)
    
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}: Process management")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL PROCESS MANAGEMENT TESTS PASSED!")
        print("   Issue is likely in test execution, not process management")
    else:
        print("\n💥 PROCESS MANAGEMENT ISSUES FOUND!")
        print("   Hanging is likely due to process startup/shutdown problems")
    
    return all_passed

if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "comprehensive":
            success = run_comprehensive_tests()
        elif sys.argv[1] == "noop":
            success = run_noop_process_tests()
        else:
            print("Usage: test_server_start_stop.py [comprehensive|noop]")
            sys.exit(1)
    else:
        success = test_server_lifecycle()
    
    print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)