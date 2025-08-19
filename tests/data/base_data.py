"""
Database operations and test data management.
Handles test data creation and saving across all entities.
"""

from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from .user_data import UserDataFactory
from .account_data import AccountDataFactory

# Registry for factory discovery
DATA_FACTORIES = {
    'user': UserDataFactory,
    'account': AccountDataFactory,
}


class DataFactory:
    """Static factory interface for getting test data records"""
    
    @staticmethod
    def get_data_record(entity_type: str, record_id: str) -> Dict[str, Any]:
        """Get test data record by entity type and ID.
        
        Args:
            entity_type: Entity type (e.g. 'user', 'account')
            record_id: Record ID to retrieve
            
        Returns:
            Dictionary containing the test data record, or empty dict if not found
        """
        entity_lower = entity_type.lower()
        
        # if entity_lower not in DATA_FACTORIES:
        #     return {}
            
        factory_class = DATA_FACTORIES[entity_lower]
        
        # Call the factory's get_test_record_by_id method
        if hasattr(factory_class, 'get_test_record_by_id'):
            return factory_class.get_test_record_by_id(record_id) or {}
        
        return {}


def initialize_metadata_cache(verbose: bool = False) -> None:
    """Initialize entity metadata cache exactly once for all entities."""
    from app.metadata import register_entity_metadata, get_entity_metadata
    
    for entity_name in DATA_FACTORIES.keys():
        # Check if already initialized
        if get_entity_metadata(entity_name):
            continue
            
        if verbose:
            print(f"🔧 Initializing metadata for {entity_name}...")
            
        model_class = utils.get_model_class(entity_name.capitalize())
        raw_metadata = model_class.get_metadata() or {}
        register_entity_metadata(entity_name, raw_metadata)
        
        if verbose:
            print(f"✅ Registered metadata for {entity_name}")


async def save_test_data(config_file: str, verbose: bool = False) -> bool:
    """
    Save test data for all entities using proper SOC.
    1. Each entity factory generates its own data 
    2. Apply metadata field management to each entity's data
    3. Initialize DB once, save all data, close DB once
    """
    try:
        # Import required modules
        from app.config import Config
        from app.db import DatabaseFactory
        
        if verbose:
            print("🧹 Creating fresh test data for all entities...")
        
        # Step 1: Each entity generates its own data
        all_entity_data = {}
        for entity_name, factory_class in DATA_FACTORIES.items():
            if verbose:
                print(f"  📝 Generating data for {entity_name}...")
            
            # Factory generates its own data with its own good/bad counts
            factory_class.generate_data()
            # Get all records from static test_scenarios
            all_scenarios = factory_class.test_scenarios
            valid_records = [record for record_id, record in all_scenarios.items() if not ("bad_" in record_id or "expired_" in record_id or "multiple_errors" in record_id)]
            invalid_records = [record for record_id, record in all_scenarios.items() if ("bad_" in record_id or "expired_" in record_id or "multiple_errors" in record_id)]
            all_records = valid_records + invalid_records
            
            if verbose:
                print(f"    Generated {len(valid_records)} valid + {len(invalid_records)} invalid records")
            
            all_entity_data[entity_name] = all_records
        
        # Step 2: Initialize metadata cache and apply metadata-driven field management
        from app.metadata import register_entity_metadata, get_entity_metadata
        
        for entity_name, records in all_entity_data.items():
            if verbose:
                print(f"  🔧 Initializing metadata and applying field management for {entity_name}...")
            
            model_class = utils.get_model_class(entity_name.capitalize())
            
            # Initialize metadata cache exactly once per entity
            entity_metadata = get_entity_metadata(entity_name)
            if not entity_metadata:
                raw_metadata = model_class.get_metadata() or {}
                register_entity_metadata(entity_name, raw_metadata)
                if verbose:
                    print(f"    ✅ Registered metadata for {entity_name}")
            
            for record in records:
                apply_metadata_fields(record, model_class, verbose)
        
        # Step 3: Initialize DB once, save all data, close DB once  
        config = Config.initialize(config_file)
        db_type: str = config.get('database', '')
        db_uri: str = config.get('db_uri', '')
        db_name: str = config.get('db_name', '')
        
        await DatabaseFactory.initialize(db_type, db_uri, db_name)
        
        total_saved = 0
        for entity_name, records in all_entity_data.items():
            if verbose:
                print(f"  💾 Saving {len(records)} {entity_name} records to database...")
            
            saved_count = 0
            for i, record in enumerate(records):
                try:
                    result, warnings = await DatabaseFactory.save_document(entity_name, record, [])
                    if result:
                        saved_count += 1
                        if warnings and verbose:
                            print(f"      ⚠️ Record {record.get('id', i+1)} warnings: {warnings}")
                            
                except Exception as e:
                    if verbose:
                        print(f"      ⚠️ Failed to save record {record.get('id', i+1)}: {e}")
            
            total_saved += saved_count
            if verbose:
                print(f"    ✅ Saved {saved_count}/{len(records)} {entity_name} records")
        
        await DatabaseFactory.close()
        
        if verbose:
            print(f"✅ Total saved: {total_saved} records across all entities")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save test data: {e}")
        try:
            await DatabaseFactory.close()
        except:
            pass
        return False


def apply_metadata_fields(record: Dict[str, Any], model_class, verbose: bool = False) -> None:
    """
    Apply metadata-driven field management for any entity.
    Handles required, autogenerate, and autocreate datetime fields.
    """
    try:
        from datetime import datetime, timezone
        import uuid
        
        metadata = model_class.get_metadata()
        fields = metadata.get('fields', {})
        current_time = datetime.now(timezone.utc)
        
        for field_name, field_info in fields.items():
            field_type = field_info.get('type')
            
            # Only process datetime/date fields
            if field_type not in ['Datetime', 'Date']:
                continue
            
            is_required = field_info.get('required', False)
            is_autogen = field_info.get('autoGenerate', False)
            is_autocreate = field_info.get('autoUpdate', False)  # This might be autocreate
            
            # Apply field management logic
            if is_autogen or is_autocreate:
                # Auto-generated/created fields - always set to current time
                record[field_name] = current_time
                    
            elif is_required and field_name not in record:
                # Required field missing - set to current time
                record[field_name] = current_time
                if verbose:
                    print(f"        📅 Required {field_name} = {current_time}")
                    
            elif field_name in record and isinstance(record[field_name], str):
                # Convert string datetime to proper datetime object if needed
                try:
                    if 'T' in record[field_name]:  # ISO format
                        record[field_name] = datetime.fromisoformat(record[field_name].replace('Z', '+00:00'))
                except ValueError:
                    # If conversion fails, use current time
                    record[field_name] = current_time
                    if verbose:
                        print(f"        🔄 Converted {field_name} to datetime")
        
        # Ensure record has an ID
        if 'id' not in record or not record['id']:
            import uuid
            record['id'] = f"generated_{uuid.uuid4().hex[:12]}"
            if verbose:
                print(f"        🆔 Generated ID: {record['id']}")
                
    except Exception as e:
        if verbose:
            print(f"        ⚠️ Error applying datetime fields: {e}")