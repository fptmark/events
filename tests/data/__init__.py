"""
Data generation package for test framework.

Provides unified data generation interface for all entities with separation of concerns:
- BaseDataFactory: Abstract interface for data generation
- ResponseGenerator: Handles complex expected response logic  
- Entity-specific factories: Fixed test scenarios + dynamic generation
- Registry pattern for factory discovery
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class BaseDataFactory(ABC):
    """Abstract base class for entity data generation"""
    
    # Test scenarios and test cases - initialized at runtime
    test_scenarios = {}
    test_cases = {}
    _initialized = False
    
    @classmethod
    def initialize_all(cls):
        """Initialize everything - scenarios and TestCase objects. Called once from constructor."""
        if cls._initialized:
            return
            
        # Initialize test scenarios from entity data factories
        from .user_data import UserDataFactory
        from .account_data import AccountDataFactory
        
        # Get test scenarios from each entity data factory
        cls.test_scenarios = {}
        cls.test_scenarios.update(UserDataFactory.get_test_scenarios())
        cls.test_scenarios.update(AccountDataFactory.get_test_scenarios())
        
        # Initialize all TestCase objects - maintaining SOC by importing here
        from tests.test_basic import BasicAPITester
        from tests.test_view import ViewParameterTester
        from tests.test_pagination import PaginationTester
        from tests.test_sorting import SortingTester
        from tests.test_filtering import FilteringTester
        from tests.test_combinations import CombinationTester
        
        # Initialize all TestCase objects
        BasicAPITester.initialize_test_cases()
        ViewParameterTester.initialize_test_cases()
        PaginationTester.initialize_test_cases()
        SortingTester.initialize_test_cases()
        FilteringTester.initialize_test_cases()
        CombinationTester.initialize_test_cases()
        
        cls._initialized = True
    
    @classmethod
    def get_test_record_by_id(cls, record_id: str) -> Optional[Dict]:
        """Universal lookup for any entity test scenario - simple and fast"""
        record = cls.test_scenarios.get(record_id)
        return record.copy() if record else None
    
    @classmethod
    def register_test_cases(cls, test_type: str, test_cases: List):
        """Register TestCase objects created by test suite classes"""
        cls.test_cases[test_type] = test_cases
    
    @classmethod
    def get_test_cases(cls, test_type: str) -> List:
        """Retrieve pre-created TestCase objects - NO CREATION, just retrieval"""
        return cls.test_cases.get(test_type, [])
    
    @abstractmethod
    def generate_data(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Generate ALL data (fixed + random) for this entity.
        Each factory controls its own good/bad counts.
        
        Returns:
            Tuple of (valid_records, invalid_records)
        """
        pass


# Import entity factories
from .user_data import UserDataFactory
from .account_data import AccountDataFactory

# Registry for factory discovery
DATA_FACTORIES = {
    'user': UserDataFactory,
    'account': AccountDataFactory,
}

def get_data_factory(entity_name: str) -> BaseDataFactory:
    """Get appropriate data factory for entity"""
    factory_class = DATA_FACTORIES.get(entity_name.lower())
    if not factory_class:
        raise ValueError(f"No data factory found for entity: {entity_name}")
    return factory_class()