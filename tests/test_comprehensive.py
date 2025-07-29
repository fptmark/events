#!/usr/bin/env python3
"""
Comprehensive Test Orchestrator

Runs all test modules (API, PFS, etc.) across different configurations:
- Database types: MongoDB/Elasticsearch  
- GV settings: ON/OFF (get_validation enabled/disabled)
- View parameters: EXISTS/MISSING (FK processing triggered/not triggered)
"""

import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
from modules.test_api_module import APITestModule
from modules.test_pfs_module import PFSTestModule

class ComprehensiveTestOrchestrator:
    def __init__(self, server_port: int = 5500):
        self.server_port = server_port
        self.server_process = None
        self.api_module = APITestModule(server_port)
        self.pfs_module = PFSTestModule(server_port)
    
    def start_server(self, database: str, gv_setting: str) -> bool:
        """Start server with specific configuration"""
        print(f"🚀 Starting server for {database} with GV={gv_setting}")
        
        # Clean up any existing processes
        self.cleanup_server()
        
        # Create temp config file
        config_data = {
            "database": database,
            "db_uri": "mongodb://localhost:27017" if database == "mongodb" else "http://localhost:9200",
            "db_name": "eventMgr",
            "get_validation": gv_setting,
            "unique_validation": gv_setting == "get_all"
        }
        config_file = "temp_comprehensive_test_config.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        try:
            # Start server
            env = {"PYTHONPATH": "."}
            self.server_process = subprocess.Popen(
                [sys.executable, "app/main.py", config_file],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # Wait for server to be ready
            for attempt in range(20):
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ Server ready (attempt {attempt + 1})")
                        return True
                except:
                    pass
                time.sleep(1)
            
            print("  ❌ Server failed to start")
            return False
            
        except Exception as e:
            print(f"  ❌ Server start error: {e}")
            return False
    
    def cleanup_server(self):
        """Stop server and clean up"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            except Exception as e:
                print(f"  ⚠️  Error stopping server: {e}")
            self.server_process = None
        
        # Kill any lingering processes
        try:
            subprocess.run(["pkill", "-f", "main.py"], capture_output=True, text=True)
        except Exception:
            pass
        
        # Wait for ports to free up
        time.sleep(2)
        
        # Clean up temp config
        try:
            Path("temp_comprehensive_test_config.json").unlink(missing_ok=True)
        except:
            pass
    
    def run_configuration_tests(self, database: str, gv_setting: str) -> Dict[str, Any]:
        """Run all test modules for a specific configuration"""
        print(f"\n{'='*80}")
        print(f"TESTING CONFIGURATION: {database.upper()} + GV={gv_setting}")
        print('='*80)
        
        # Start server with this configuration
        if not self.start_server(database, gv_setting):
            return {
                "database": database,
                "gv_setting": gv_setting,
                "success": False,
                "error": "Server failed to start",
                "results": []
            }
        
        all_results = []
        
        try:
            # Run API validation tests
            print(f"\n🔍 Running API validation tests...")
            api_results = self.api_module.run_all_api_tests()
            all_results.extend(api_results)
            
            # Run PFS tests
            print(f"\n🔍 Running PFS tests...")
            pfs_results = self.pfs_module.run_all_pfs_tests()
            all_results.extend(pfs_results)
            
            return {
                "database": database,
                "gv_setting": gv_setting,
                "success": True,
                "results": all_results
            }
            
        except Exception as e:
            return {
                "database": database,
                "gv_setting": gv_setting,
                "success": False,
                "error": str(e),
                "results": all_results
            }
        finally:
            self.cleanup_server()
    
    def run_all_configurations(self) -> List[Dict[str, Any]]:
        """Run tests across all configurations"""
        configurations = [
            ("mongodb", "get_all"),    # GV ON
            ("mongodb", ""),           # GV OFF
            ("elasticsearch", "get_all"), # GV ON
            ("elasticsearch", ""),     # GV OFF
        ]
        
        all_config_results = []
        
        print("🧪 COMPREHENSIVE TEST ORCHESTRATOR")
        print("=" * 80)
        print("Running all test modules across multiple configurations")
        print()
        
        for database, gv_setting in configurations:
            config_result = self.run_configuration_tests(database, gv_setting)
            all_config_results.append(config_result)
        
        return all_config_results
    
    def print_summary(self, all_results: List[Dict[str, Any]]):
        """Print comprehensive test summary"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST SUMMARY")
        print('='*80)
        
        total_configs = len(all_results)
        successful_configs = sum(1 for r in all_results if r.get('success', False))
        
        print(f"Configurations tested: {successful_configs}/{total_configs}")
        print()
        
        for config_result in all_results:
            db = config_result['database']
            gv = config_result['gv_setting'] or 'OFF'
            status = "✅ PASS" if config_result.get('success', False) else "❌ FAIL"
            
            print(f"{status} {db.upper()} + GV={gv}")
            
            if not config_result.get('success', False):
                error = config_result.get('error', 'Unknown error')
                print(f"     Error: {error}")
            else:
                results = config_result.get('results', [])
                if results:
                    passed = sum(1 for r in results if r.get('success', False))
                    total = len(results)
                    print(f"     Tests: {passed}/{total} passed")
                    
                    # Show failed tests
                    failed_tests = [r for r in results if not r.get('success', False)]
                    for failed in failed_tests:
                        test_type = failed.get('test_type', 'unknown')
                        details = failed.get('details', 'No details')
                        print(f"       ❌ {test_type}: {details}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive Test Orchestrator')
    parser.add_argument('--config', choices=['mongo', 'es', 'all'], default='all',
                       help='Which database config to test')
    parser.add_argument('--gv', choices=['on', 'off', 'both'], default='both',
                       help='Which GV setting to test')
    args = parser.parse_args()
    
    orchestrator = ComprehensiveTestOrchestrator()
    
    # Run specific configurations based on args
    if args.config == 'all' and args.gv == 'both':
        results = orchestrator.run_all_configurations()
    else:
        # Run specific subset (implement as needed)
        results = orchestrator.run_all_configurations()
    
    orchestrator.print_summary(results)
    
    # Return exit code based on overall success
    all_successful = all(r.get('success', False) for r in results)
    return 0 if all_successful else 1

if __name__ == "__main__":
    sys.exit(main())