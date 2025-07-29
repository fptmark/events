#!/usr/bin/env python3
"""
Validation Test Framework - Dry Run Mode

Generates all test scenarios and curl commands without needing a live server.
Shows the comprehensive test structure we'll run.
"""

import sys
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class TestScenario:
    """Test scenario definition"""
    name: str
    description: str
    url_path: str
    expected_validations: List[str]
    configuration: str  # e.g., "MongoDB+GV_OFF"

class ValidationTestGenerator:
    def __init__(self):
        self.server_url = "http://localhost:5500"
        self.test_user_id = "68814e0e73b517d9e048b093"
    
    def _decode_url_for_display(self, url: str) -> str:
        """Decode URL parameters for readable display"""
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.query:
                return url
            
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            decoded_params = []
            
            for key, values in params.items():
                for value in values:
                    decoded_value = urllib.parse.unquote(value)
                    decoded_params.append(f"{key}={decoded_value}")
            
            decoded_query = "&".join(decoded_params)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{decoded_query}"
        except:
            return url
    
    def generate_scenarios_for_config(self, config_name: str, gv_enabled: bool) -> List[TestScenario]:
        """Generate test scenarios for a specific server configuration"""
        
        base_path = f"/api/user/{self.test_user_id}"
        view_param = urllib.parse.quote('{"account":["id"]}')
        
        scenarios = [
            # 1. Basic validation tests
            TestScenario(
                name=f"{config_name}_enum_validation",
                description="Test bad enum value (should always show validation error)",
                url_path=base_path,
                expected_validations=["gender"],
                configuration=config_name
            ),
            
            TestScenario(
                name=f"{config_name}_currency_validation",
                description="Test negative currency value (should always show validation error)",
                url_path=base_path,
                expected_validations=["netWorth"],
                configuration=config_name
            ),
            
            # 2. FK validation (depends on GV setting)
            TestScenario(
                name=f"{config_name}_fk_no_view",
                description=f"Test bad FK without view (should {'work' if gv_enabled else 'NOT work'} with GV={'ON' if gv_enabled else 'OFF'})",
                url_path=base_path,
                expected_validations=["accountId"] if gv_enabled else [],
                configuration=config_name
            ),
            
            # 3. FK validation with view (should always work)
            TestScenario(
                name=f"{config_name}_fk_with_view",
                description="Test bad FK with view parameter (should always work)",
                url_path=f"{base_path}?view={view_param}",
                expected_validations=["accountId"],
                configuration=config_name
            ),
            
            # 4. Multiple validations with view
            TestScenario(
                name=f"{config_name}_multiple_validations",
                description="Test multiple validation errors together",
                url_path=f"{base_path}?view={view_param}",
                expected_validations=["gender", "netWorth", "accountId"],
                configuration=config_name
            ),
            
            # 5. Validation with PFS parameters
            TestScenario(
                name=f"{config_name}_validation_pfs",
                description="Test validation with pagination/filtering/sorting",
                url_path=f"{base_path}?page=1&pageSize=5&sort=username&order=asc",
                expected_validations=["gender", "netWorth"],
                configuration=config_name
            ),
            
            # 6. Complex: All parameters together
            TestScenario(
                name=f"{config_name}_complex_all",
                description="Test validation with view + PFS parameters",
                url_path=f"{base_path}?view={view_param}&page=1&pageSize=3&sort=createdAt&order=desc",
                expected_validations=["gender", "netWorth", "accountId"],
                configuration=config_name
            ),
            
            # 7. List endpoint tests
            TestScenario(
                name=f"{config_name}_list_filter",
                description="Test list endpoint with filter for validation",
                url_path=f"/api/user?filter=id:{self.test_user_id}&pageSize=5",
                expected_validations=["gender", "netWorth"] + (["accountId"] if gv_enabled else []),
                configuration=config_name
            ),
            
            # 8. List with view and filter
            TestScenario(
                name=f"{config_name}_list_view_filter",
                description="Test list with view and filter",
                url_path=f"/api/user?view={view_param}&filter=id:{self.test_user_id}&pageSize=3",
                expected_validations=["gender", "netWorth", "accountId"],
                configuration=config_name
            ),
            
            # 9. Complex filter scenarios
            TestScenario(
                name=f"{config_name}_complex_filter",
                description="Test complex filter with validation",
                url_path=f"/api/user?filter=id:{self.test_user_id},gender:male&pageSize=5",
                expected_validations=["netWorth"] + (["accountId"] if gv_enabled else []),
                configuration=config_name
            ),
            
            # 10. Intensive FK processing
            TestScenario(
                name=f"{config_name}_fk_intensive",
                description="Test intensive FK processing with complex view",
                url_path=f"{base_path}?view={urllib.parse.quote('{\"account\":[\"id\",\"createdAt\",\"updatedAt\"]}')}",
                expected_validations=["accountId"],
                configuration=config_name
            )
        ]
        
        return scenarios
    
    def generate_all_scenarios(self) -> List[TestScenario]:
        """Generate all test scenarios for all 4 server configurations"""
        
        configurations = [
            ("MongoDB_GV_OFF", False),
            ("MongoDB_GV_ON", True),
            ("Elasticsearch_GV_OFF", False), 
            ("Elasticsearch_GV_ON", True)
        ]
        
        all_scenarios = []
        
        for config_name, gv_enabled in configurations:
            config_scenarios = self.generate_scenarios_for_config(config_name, gv_enabled)
            all_scenarios.extend(config_scenarios)
        
        return all_scenarios
    
    def generate_curl_file(self, scenarios: List[TestScenario], filename: str = "comprehensive_validation_curl.sh"):
        """Generate comprehensive curl file"""
        
        with open(filename, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('# Comprehensive Validation Test Matrix - All 40+ Scenarios\n')
            f.write('# Generated by test_validation_dry_run.py\n')
            f.write('# 4 Server Configurations × 10 Test Cases Each = 40 Total Tests\n')
            f.write('#\n')
            f.write('# Server Configurations:\n')
            f.write('# 1. MongoDB + GV OFF\n')
            f.write('# 2. MongoDB + GV ON\n')
            f.write('# 3. Elasticsearch + GV OFF\n')
            f.write('# 4. Elasticsearch + GV ON\n')
            f.write('#\n')
            f.write('# Run: chmod +x comprehensive_validation_curl.sh && ./comprehensive_validation_curl.sh\n\n')
            
            # Group by configuration
            by_config = {}
            for scenario in scenarios:
                config = scenario.configuration
                if config not in by_config:
                    by_config[config] = []
                by_config[config].append(scenario)
            
            for config_name, config_scenarios in by_config.items():
                f.write(f'# ===============================================\n')
                f.write(f'# {config_name} - {len(config_scenarios)} Test Cases\n')
                f.write(f'# ===============================================\n\n')
                
                for i, scenario in enumerate(config_scenarios, 1):
                    url = f"{self.server_url}{scenario.url_path}"
                    decoded_url = self._decode_url_for_display(url)
                    
                    f.write(f'# Test {i}: {scenario.name}\n')
                    f.write(f'# Description: {scenario.description}\n')
                    f.write(f'# Expected validations: {", ".join(scenario.expected_validations) if scenario.expected_validations else "None"}\n')
                    f.write(f'echo "=== {config_name} Test {i}: GET {decoded_url} ==="\n')
                    f.write(f'curl -X GET "{url}"\n')
                    f.write('echo ""\n\n')
                
                f.write('\n')
        
        print(f"📁 Generated {filename} with {len(scenarios)} test scenarios")
    
    def print_test_matrix_summary(self, scenarios: List[TestScenario]):
        """Print summary of the test matrix"""
        
        print("🧪 COMPREHENSIVE VALIDATION TEST MATRIX")
        print("=" * 80)
        
        # Group by configuration
        by_config = {}
        for scenario in scenarios:
            config = scenario.configuration
            if config not in by_config:
                by_config[config] = []
            by_config[config].append(scenario)
        
        print(f"Total Test Scenarios: {len(scenarios)}")
        print(f"Server Configurations: {len(by_config)}")
        print()
        
        for config_name, config_scenarios in by_config.items():
            print(f"📋 {config_name}: {len(config_scenarios)} test cases")
            
            # Show test case breakdown
            validation_types = {}
            for scenario in config_scenarios:
                for validation in scenario.expected_validations:
                    if validation not in validation_types:
                        validation_types[validation] = 0
                    validation_types[validation] += 1
            
            if validation_types:
                print(f"   Validation coverage: {dict(validation_types)}")
            print()
        
        # Show validation coverage across all tests
        all_validations = set()
        for scenario in scenarios:
            all_validations.update(scenario.expected_validations)
        
        print(f"Field Validation Coverage: {sorted(all_validations)}")
        print()
        
        # Show test complexity breakdown
        simple_tests = [s for s in scenarios if '?' not in s.url_path]
        view_tests = [s for s in scenarios if 'view=' in s.url_path]
        pfs_tests = [s for s in scenarios if any(param in s.url_path for param in ['page=', 'sort=', 'filter='])]
        
        print("Test Complexity Breakdown:")
        print(f"  Simple GET tests: {len(simple_tests)}")
        print(f"  Tests with view parameters: {len(view_tests)}")
        print(f"  Tests with PFS parameters: {len(pfs_tests)}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validation Test Framework - Dry Run')
    parser.add_argument('--curl-file', default='comprehensive_validation_curl.sh',
                       help='Output curl file name')
    args = parser.parse_args()
    
    generator = ValidationTestGenerator()
    
    try:
        # Generate all test scenarios
        scenarios = generator.generate_all_scenarios()
        
        # Print summary
        generator.print_test_matrix_summary(scenarios)
        
        # Generate curl file
        generator.generate_curl_file(scenarios, args.curl_file)
        
        print("=" * 80)
        print("✅ DRY RUN COMPLETE")
        print(f"📁 Curl commands saved to: {args.curl_file}")
        print("📊 Test matrix summary printed above")
        print()
        print("Next steps:")
        print("1. Start server with desired configuration (MongoDB/ES + GV ON/OFF)")
        print(f"2. Run: chmod +x {args.curl_file} && ./{args.curl_file}")
        print("3. Examine curl output for validation notifications")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Dry run failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())