#!/usr/bin/env python3
"""
Comprehensive test runner that orchestrates all test files across 4 modes.
Supports server lifecycle management, data creation, and multiple test modes.
"""

import sys
import os
import subprocess
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

import json5

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import TestCounter
from tests.suites.test_basic import BasicAPITester
from tests.suites.test_view import ViewParameterTester
from tests.suites.test_pagination import PaginationTester
from tests.suites.test_sorting import SortingTester
from tests.suites.test_filtering import FilteringTester
from tests.suites.test_combinations import CombinationTester
from tests.suites.test_lowercase_params import LowercaseParamTester
from tests.curl import CurlManager
from tests.data.validation import Validator
from app.config import Config

# Initialize metadata cache at module import time
from tests.data.base_data import initialize_metadata_cache
initialize_metadata_cache()

@dataclass
class TestConfig:
    name: str
    database: str 
    config_data: dict

@dataclass
class TestResult:
    config_name: str
    success: bool
    passed: int
    failed: int
    total: int
    duration: float
    error: Optional[str] = None

# Global state
server_process: subprocess.Popen[str] = None
server_port = 5500
    
def cleanup_port():
    """Kill any processes using our port"""
    try:
        subprocess.run(["pkill", "-f", "main.py"], check=False)
        time.sleep(1)
    except:
        pass
    
async def start_server(config_data: dict, verbose: bool = False) -> bool:
    """Start server with given config data"""
    global server_process
    cleanup_port()
    if verbose:
        print(f"🚀 Starting server with {config_data.get('database', 'unknown')} config")
    else:
        print(f"🚀 Starting server...")
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        config_json = json.dumps(config_data)
        
        server_process = subprocess.Popen(
            [sys.executable, "app/main.py", "--config-json", config_json],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        success = False
        # Wait for server to be ready
        from tests.base_test import BaseTestFramework
        for attempt in range(30):
            if BaseTestFramework.check_server_health(f"http://localhost:{server_port}", timeout=2):
                success = True
                if verbose:
                    print(f"  ✅ Server ready (attempt {attempt + 1})")
                break
            time.sleep(1)
        
        if not success:
            print("  ❌ Server failed to start")
            return False
        
    except Exception as e:
        print(f"  ❌ Server start error: {e}")
        return False

    return True
    
async def create_data(config_data: dict, verbose: bool = False) -> bool:
    """Create fresh test data (includes wipe)"""
    print("🔄 Creating fresh test data (includes wipe)...")
    success = await wipe_data(config_data, verbose)
    if not success:
        print(f"❌ Failed to wipe data")
        return False
        
    # Initialize database exactly like the app does (ES templates, indices, constraints)  
    print("🔧 Initializing database like the main app...")
    try:
        from app.db import DatabaseFactory
        from app.config import Config
        from app.services.metadata import MetadataService
        from app.services.model import ModelService
        
        # Same ENTITIES list as main.py
        ENTITIES = ["Account", "User", "Profile", "TagAffinity", "Event", "UserEvent", "Url", "Crawl"]
        
        # Initialize services like the app does
        MetadataService.initialize(ENTITIES)
        ModelService.initialize(ENTITIES)
        
        # Initialize database connection
        db_type, db_uri, db_name = Config.get_db_params(config_data)
        db_instance = await DatabaseFactory.initialize(db_type, db_uri, db_name)
        
        # Initialize database structures (indexes, templates, etc.)
        success = await db_instance.indexes.initialize()
        if not success:
            print("⚠️ Database initialization returned failure (continuing anyway)")
        
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    
    success = await create_test_data(config_data, verbose)
    if not success:
        print(f"❌ Failed to create test data")
        return False
    return True

def stop_server(verbose: bool = False):
    """Stop the server"""
    global server_process
    if verbose:
        print("🛑 Stopping server")
    if server_process:
        try:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
        except:
            pass
        server_process = None
    cleanup_port()
    time.sleep(1)
    
    
async def create_test_data(config_data: dict, verbose: bool = False) -> bool:
    """Create test data using unified data factory approach"""
    try:
        from tests.data.base_data import save_test_data
        
        success = await save_test_data(config_data, verbose)
        
        if success:
            if verbose:
                print("  ✅ Test data created successfully for all entities")
            return True
        else:
            print("  ❌ Test data creation failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Test data creation error: {e}")
        return False
    
async def wipe_data(config_data: dict, verbose: bool = False) -> bool:
    """Wipe all data using direct database calls"""
    print("🧹 Wiping all data...")
    print(f"\n📋 Wiping data")

    try:
        from app.db import DatabaseFactory
        from app.config import Config
        
        # Get database parameters
        db_type, db_uri, db_name = Config.get_db_params(config_data)
        
        await DatabaseFactory.initialize(db_type, db_uri, db_name)
        
        # Get entities from MetadataService
        from app.services.metadata import MetadataService
        entities = MetadataService.list_entities()
        wiped_entities = []
        failed_entities = []
        
        for entity in entities:
            try:
                success = await DatabaseFactory.remove_entity(entity)
                if success:
                    wiped_entities.append(entity)
                    if verbose:
                        print(f"   🗑️ Dropped collection: {entity}")
                else:
                    failed_entities.append(entity)
                    print(f"   ⚠️ Failed to drop collection: {entity}")
            except Exception as e:
                failed_entities.append(entity)
                print(f"   ❌ Error dropping collection {entity}: {e}")
        
        if failed_entities:
            print(f"❌ Data wipe failed for: {', '.join(failed_entities)}")
            return False
        else:
            print(f"✅ All data wiped successfully: {', '.join(wiped_entities)}")
            return True
            
    except Exception as e:
        print(f"❌ Data wipe error: {e}")
        return False
    

async def generate_curl(test_cases: Dict[str, Tuple[str, type]], verbose: bool = False):
    """Generate curl.sh only - no server, no data, no validation"""  
    print(f"📝 Generating curl.sh with unique URLs...")
    curl = CurlManager(verbose)
    curl.create_curl_script()
    
    for test_name, (test_description, test_class) in test_cases.items():
        if verbose:
            print(f"  📝 Generating {test_description}...")
        
        # Get test cases from static method
        test_cases_list = test_class.get_test_cases()
        
        # Write each test case directly to curl file
        curl_file = curl.get_curl_file_handle()
        if curl_file:
            curl_file.write(f"# ========== {test_description} ==========\n")
            for test_case in test_cases_list:
                full_url = f"http://localhost:{server_port}{test_case.url}"
                curl_file.write(f'execute_url "{test_case.method}" "{full_url}" "{test_case.description}"\n')
    
    # Close curl file
    curl.close_curl_file()
    
    print("✅ curl.sh generation complete")

async def test_connection(config_data: dict, verbose: bool = False) -> bool:
    """Run no-op connectivity test"""
    print("🔗 Running connectivity test...")
    start_time = time.time()
    print(f"  📋 Testing configuration: {config_data.get('database', 'unknown')}")
    await start_server(config_data, verbose)
    from tests.base_test import BaseTestFramework
    if not BaseTestFramework.check_server_health(f"http://localhost:{server_port}", timeout=5):
        return False
    stop_server(verbose)
    end_time = time.time()
    print(f"  ✅ Connectivity test completed in {end_time - start_time:.1f}s")
    return True


async def validate_curl_results(test_cases: Dict[str, Tuple[str, type]], config_data: dict, url: str = None, results_data: dict = None, verbose: bool = False) -> bool:
    """Validate curl results data"""
    results = results_data

    total_counter = TestCounter()

    # Use config_data directly for validation
    Config._config = config_data
    config = Config._config
    
    for test_type, (test_description, test_class) in test_cases.items():
        if url is None:
            print(f"\n🧪 Running {test_description} tests...")
        
        # Get test cases from static method
        test_cases_list = test_class.get_test_cases()
        
        suite_counter = TestCounter()
        
        for test in test_cases_list:
            if url and url.lower() != test.url.lower():
                continue
            if verbose or url:
                print(f"  📝 Processing {test.description}...    {test.url}")
            
            try:
                if results is None:
                    # Live HTTP request - returns (status_code, dict)
                    full_url = f"http://localhost:{server_port}{test.url}"
                    http_status, result = CurlManager.make_api_request(test.method, full_url)
                else:
                    # Use file results - status is int, need to compare
                    url_key = test.url
                    if url_key in results:
                        result = results[url_key]['response']
                        http_status = results[url_key]['status']
                    else:
                        print(f"  ❌ {test.description} - URL not found in results")
                        http_status, result = -1, None
                
                status = http_status == test.expected_status

                if status and result:
                    validator = Validator(test, result, config, verbose)
                    if validator.validate_test_case(http_status):
                        print(f"  ✅ {test.description} passed")
                        suite_counter.pass_test()
                    else:
                        print(f"  ❌ {test.description} failed - validation mismatch")
                        suite_counter.fail_test()
                else:
                    print(f"  ❌ {test.description} failed")
                    suite_counter.fail_test()
                    
            except Exception as e:
                print(f"  ❌ {test.description} failed: {e}")
                suite_counter.fail_test()
        
        total_counter.update(suite_counter)
        # Print suite summary
        if url is None:
            print(f"  {suite_counter.summary(test_description)}")
    
    # Print overall summary
    print(f"\n{total_counter.summary('FINAL SUMMARY')}")
    
    return total_counter.failed == 0
    


def cleanup(verbose: bool = False):
    """Clean up temporary files"""
    try:
        if os.path.exists("tests/temp_test_config.json"):
            os.remove("tests/temp_test_config.json")
    except:
        pass
    stop_server(verbose)



def get_configs(dbs: List[str], config_name: str = None) -> List[Dict[Any, Any]]:
    """Get configurations based on database filters and config name"""
    all_configs = get_internal_configs()
    configs = []
    
    for config in all_configs:
        if config_name:
            if config.name == config_name:
                return [config.config_data]
            else:
                with open(config_name, 'r') as f:
                    return [json5.load(f)]
        elif dbs:
            for db in dbs:
                if config.database == db:
                    configs.append(config.config_data)

    return configs



def get_internal_configs() -> List[TestConfig]:
    """Get all internal test configurations"""
    return [
        TestConfig(
            name="mongo",
            database="mongodb",
            config_data={
                "database": "mongodb",
                "db_uri": "mongodb://localhost:27017",
                "db_name": "eventMgr",
                "server_port": 5500
            }
        ),
        TestConfig(
            name="mongov",
            database="mongodb", 
            config_data={
                "database": "mongodb",
                "db_uri": "mongodb://localhost:27017", 
                "db_name": "eventMgr",
                "validation": "multiple",
                "server_port": 5500
            }
        ),
        TestConfig(
            name="es",
            database="elasticsearch",
            config_data={
                "database": "elasticsearch",
                "db_uri": "http://localhost:9200",
                "db_name": "eventMgr", 
                "server_port": 5500
            }
        ),
        TestConfig(
            name="esv",
            database="elasticsearch",
            config_data={
                "database": "elasticsearch",
                "db_uri": "http://localhost:9200",
                "db_name": "eventMgr",
                "validation": "multiple",
                "server_port": 5500
            }
        )
    ]
    


async def main():
    """Main function with CLI order processing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive test runner')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', nargs='?', const=True, default=False,
                       help='Curl mode: no arg=generate only, "execute"=run curl.sh and validate, filename=validate from file')
    parser.add_argument('--connection', action='store_true',
                       help='Run connectivity test')
    parser.add_argument('--newdata', action='store_true',
                       help='Wipe all data and create fresh test data with known validation issues')
    parser.add_argument('--wipe', action='store_true',
                       help='Wipe all data only')
    parser.add_argument('--tests', action='store_true',
                       help='Run tests')
    parser.add_argument('--test-types', nargs='+', 
                       choices=['basic', 'view', 'page', 'filter', 'sort', 'lowercase'],
                       help='Test types to run (choices: basic, view, page, filter, sort, lowercase). Can specify multiple: --test-types basic sort')
    parser.add_argument('--delay', type=float, default=0.0,
                       help='Delay between requests in seconds (default: 0.0 - no delay)')
    parser.add_argument('--url', default=None,
                       help='specify single url to test')
    parser.add_argument('--config', 
                       help='Specify internal config [mongo, mongov, es, esv] or config file path')
    parser.add_argument('--dbs', 
                       help='Specify database(s) to test [mongodb, elasticsearch] comma-separated')
    args = parser.parse_args()
    
    # Validate arguments - require --config for operations that need it
    if (args.wipe or args.newdata or args.connection or args.tests) and not args.config:
        parser.error("--config is required for database operations")
    
    # --curl generate-only mode doesn't need config, but --curl execute does
    if args.curl and args.curl != True and args.curl == 'execute' and not args.config:
        parser.error("--config is required for --curl execute")
    
    # Initialize test system before any real work
    from tests.init import initialize_all
    initialize_all()

    test_types = args.test_types if args.test_types else ['basic', 'view', 'page', 'filter', 'sort', 'lowercase']
    from tests.suites.test_case import get_test_suites
    test_cases: Dict[str, Tuple[str, type]] = get_test_suites(test_types)

    # Parse --dbs argument and validate against known database types
    if args.dbs:
        valid_db_types = ['mongodb', 'elasticsearch']
        dbs = []
        for db in args.dbs.split(','):
            db = db.strip().lower()
            if db in valid_db_types:
                dbs.append(db)
            else:
                print(f"❌ Invalid database type: {db}. Valid types: {', '.join(valid_db_types)}")
                return 1
    else:
        dbs = []


    # Handle --curl generate-only mode without config
    if args.curl and args.curl == True and not args.config:
        await generate_curl(test_cases, args.verbose)
        return 0

    for config in get_configs(dbs, args.config):
        server_started = False
        try:
            for i, arg in enumerate(sys.argv):
                if arg == '--wipe':
                    success = await wipe_data(config, args.verbose)
                elif arg == '--newdata':
                    success = await create_data(config, args.verbose)
                elif arg == '--connection':
                    print("🔗 Running connectivity test...")
                    success = await test_connection(config, args.verbose)
                    server_started = True
                elif arg == '--curl':
                    if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
                        if sys.argv[i + 1] == 'execute':
                            await generate_curl(test_cases, args.verbose)
                            await start_server(config, args.verbose)
                            server_started = True
                            result = subprocess.run(['bash', 'tests/curl.sh'], capture_output=True, text=True, timeout=300)
                            if result.returncode != 0:
                                print(f"❌ curl.sh execution failed")
                                return 1
                            results_data = json.loads(result.stdout)
                            success = await validate_curl_results(test_cases, config, args.url, results_data, args.verbose)
                        else:
                            with open(sys.argv[i + 1], 'r') as f:
                                results_data = json.load(f)
                            success = await validate_curl_results(test_cases, config, args.url, results_data, args.verbose)
                            i += 1
                    else:
                        await generate_curl(test_cases, args.verbose)

        except Exception as e:
            print(f"❌ Operation failed: {e}")
            return 1
        
        finally:
            # Only cleanup server if we actually started one
            if server_started:
                cleanup(args.verbose)

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))