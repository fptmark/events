#!/usr/bin/env python3
"""
Test runner for Events application testing framework.

Usage:
    python run_tests.py                    # Run with mongo.json (default)
    python run_tests.py --config es.json   # Run with Elasticsearch
    python run_tests.py --all              # Run with both configs
    python run_tests.py --cleanup          # Run tests and cleanup after
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_user_validation import main as run_user_tests

def create_argument_parser():
    """Create argument parser for test runner"""
    parser = argparse.ArgumentParser(description='Events Testing Framework Runner')
    parser.add_argument('--config', default='mongo.json',
                       help='Configuration file path (default: mongo.json)')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests (default: http://127.0.0.1:5500)')
    parser.add_argument('--preserve', action='store_true',
                       help='Preserve test data after running tests (for troubleshooting)')
    parser.add_argument('--all', action='store_true',
                       help='Run tests with both mongo.json and es.json configs')
    parser.add_argument('--entity', choices=['user'], default='user',
                       help='Which entity to test (default: user)')
    return parser

async def run_tests_with_config(config_file: str, server_url: str, preserve: bool, entity: str):
    """Run tests with specific configuration"""
    print(f"\\n{'='*80}")
    print(f"RUNNING TESTS WITH CONFIG: {config_file}")
    print('='*80)
    
    # Set up sys.argv for the test module
    original_argv = sys.argv.copy()
    try:
        sys.argv = ['test_user_validation.py', config_file, '--server-url', server_url]
        if preserve:
            sys.argv.append('--preserve')
        
        if entity == 'user':
            success = await run_user_tests()
        else:
            print(f"❌ Entity '{entity}' not yet implemented")
            return False
            
        return success
        
    finally:
        sys.argv = original_argv

async def main():
    """Main test runner"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    print("🚀 Events Application Test Runner")
    print(f"Entity: {args.entity}")
    print(f"Server: {args.server_url}")
    print(f"Preserve: {args.preserve}")
    
    if args.all:
        # Run tests with both configurations
        configs = ['mongo.json', 'es.json']
        results = {}
        
        for config in configs:
            if Path(config).exists():
                print(f"\\n🔧 Testing with {config}...")
                success = await run_tests_with_config(config, args.server_url, args.preserve, args.entity)
                results[config] = success
            else:
                print(f"⚠️  Config file {config} not found, skipping...")
                results[config] = None
        
        # Summary for all configs
        print(f"\\n{'='*80}")
        print("OVERALL TEST SUMMARY")
        print('='*80)
        
        all_passed = True
        for config, result in results.items():
            if result is None:
                print(f"{config}: SKIPPED (file not found)")
            elif result:
                print(f"{config}: ✅ PASSED")
            else:
                print(f"{config}: ❌ FAILED")
                all_passed = False
        
        if all_passed:
            print("\\n🎉 ALL CONFIGURATIONS PASSED!")
        else:
            print("\\n💥 SOME CONFIGURATIONS FAILED!")
        
        return all_passed
        
    else:
        # Run tests with single configuration
        if not Path(args.config).exists():
            print(f"❌ Config file {args.config} not found")
            return False
            
        return await run_tests_with_config(args.config, args.server_url, args.preserve, args.entity)

if __name__ == "__main__":
    print("Events Test Runner")
    print("Make sure the server is running before executing tests!")
    print()
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\nTest runner failed: {e}")
        sys.exit(1)