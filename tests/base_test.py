"""
Base testing framework for Events application.
Uses the existing database abstraction layer from DatabaseFactory.
"""

import sys
import json
import requests
import asyncio
import argparse
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.db import DatabaseFactory
import app.utils as utils

@dataclass
class TestResult:
    name: str
    status: str  # "PASS" or "FAIL"
    details: str
    duration: float = 0.0

class BaseTestFramework:
    """Base test framework that can be extended for different entities"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500"):
        self.config_file = config_file
        self.server_url = server_url
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.results: List[TestResult] = []
        
        # Load config and initialize database through existing abstraction
        self.config = Config.initialize(config_file)
        self.db_type = self.config.get('database', 'mongodb')
        self.db_uri = self.config.get('db_uri', '')
        self.db_name = self.config.get('db_name', '')
        
        print(f"✅ Loaded config from {config_file}")
        print(f"   Database: {self.db_type}")
        print(f"   DB URI: {self.db_uri}")
        print(f"   DB Name: {self.db_name}")
    
    async def setup_database_connection(self):
        """Setup database connection using existing DatabaseFactory"""
        try:
            await DatabaseFactory.initialize(self.db_type, self.db_uri, self.db_name)
            print(f"✅ Database connection established via DatabaseFactory")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def cleanup_database_connection(self):
        """Close database connection"""
        try:
            if DatabaseFactory.is_initialized():
                await DatabaseFactory.close()
                print("✅ Database connection closed")
        except Exception as e:
            print(f"❌ Database cleanup failed: {e}")
    
    def test(self, name: str, test_func, expected_result=None):
        """Run a test and track results"""
        self.test_count += 1
        print(f"\\n{'='*60}")
        print(f"TEST {self.test_count}: {name}")
        print('='*60)
        
        start_time = datetime.now()
        
        try:
            result = test_func()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if expected_result is not None:
                if result == expected_result:
                    print(f"✅ PASS: {name} ({duration:.2f}s)")
                    self.passed += 1
                    self.results.append(TestResult(name, "PASS", str(result), duration))
                else:
                    print(f"❌ FAIL: {name} ({duration:.2f}s)")
                    print(f"   Expected: {expected_result}")
                    print(f"   Got: {result}")
                    self.failed += 1
                    self.results.append(TestResult(name, "FAIL", f"Expected {expected_result}, got {result}", duration))
            else:
                print(f"✅ PASS: {name} ({duration:.2f}s)")
                self.passed += 1
                self.results.append(TestResult(name, "PASS", str(result), duration))
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"❌ FAIL: {name} ({duration:.2f}s)")
            print(f"   Exception: {e}")
            self.failed += 1
            self.results.append(TestResult(name, "FAIL", str(e), duration))
    
    def summary(self):
        """Print test summary"""
        print(f"\\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed/self.test_count)*100:.1f}%" if self.test_count > 0 else "No tests run")
        
        total_duration = sum(r.duration for r in self.results)
        print(f"Total duration: {total_duration:.2f}s")
        
        if self.failed > 0:
            print(f"\\n❌ FAILED TESTS:")
            for result in self.results:
                if result.status == "FAIL":
                    print(f"  - {result.name}: {result.details}")
        
        return self.failed == 0
    
    def make_api_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Helper method for API requests"""
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            print(f"  {method} {endpoint} -> {response.status_code}")
            
            if response.status_code == expected_status:
                try:
                    return True, response.json()
                except:
                    return True, {"raw_response": response.text}
            else:
                print(f"  Expected {expected_status}, got {response.status_code}")
                try:
                    return False, response.json()
                except:
                    return False, {"error": response.text}
                    
        except Exception as e:
            print(f"  Request failed: {e}")
            return False, {"exception": str(e)}
    
    async def insert_invalid_document(self, collection_name: str, document: Dict) -> bool:
        """Insert a document directly via DatabaseFactory bypassing validation"""
        try:
            # Use DatabaseFactory to save directly, bypassing model validation
            result, warnings = await DatabaseFactory.save_document(collection_name, document, [])
            print(f"✅ Inserted invalid document directly via DatabaseFactory")
            if warnings:
                print(f"   Warnings: {warnings}")
            return True
        except Exception as e:
            print(f"❌ Failed to insert document via DatabaseFactory: {e}")
            return False
    
    async def get_document_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict]:
        """Get a document directly via DatabaseFactory"""
        try:
            doc, warnings = await DatabaseFactory.get_by_id(collection_name, doc_id, [])
            if warnings:
                print(f"   Warnings on get: {warnings}")
            return doc
        except Exception as e:
            print(f"❌ Failed to get document via DatabaseFactory: {e}")
            return None
    
    async def cleanup_test_data(self, collection_name: str, filter_criteria: Dict):
        """Clean up test data via DatabaseFactory"""
        try:
            # For cleanup, we'll need to get documents first, then delete them by ID
            # This mimics the model delete behavior
            if "username" in filter_criteria:
                # Find test users by username pattern
                all_docs, warnings, count = await DatabaseFactory.get_all(collection_name, [])
                deleted_count = 0
                for doc in all_docs:
                    if any(filter_criteria[key] in str(doc.get(key, "")) for key in filter_criteria):
                        doc_id = DatabaseFactory.get_id(doc)
                        if doc_id:
                            success = await DatabaseFactory.delete_document(collection_name, doc_id)
                            if success:
                                deleted_count += 1
                print(f"🧹 Cleaned up {deleted_count} test documents")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

    @staticmethod
    def create_argument_parser():
        """Create argument parser for tests"""
        parser = argparse.ArgumentParser(description='Events Testing Framework')
        parser.add_argument('config_file', nargs='?', default='mongo.json',
                           help='Configuration file path (default: mongo.json)')
        parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                           help='Server URL for API tests (default: http://127.0.0.1:5500)')
        parser.add_argument('--cleanup', action='store_true',
                           help='Clean up test data after running tests')
        return parser