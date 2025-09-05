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

from .user_data import UserDataFactory
from .account_data import AccountDataFactory


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
        
        if entity_lower == 'user':
            return UserDataFactory.get_test_record_by_id(record_id) or {}
        elif entity_lower == 'account':
            return AccountDataFactory.get_test_record_by_id(record_id) or {}
        
        return {}


def initialize_metadata_cache(verbose: bool = False) -> None:
    """Initialize entity metadata cache exactly once for all entities."""
    from app.services.metadata import MetadataService
    
    # Initialize MetadataService with all entity names (same as main.py)
    ENTITIES = [
        "Account",
        "User", 
        "Profile",
        "TagAffinity",
        "Event",
        "UserEvent",
        "Url",
        "Crawl",
    ]
    MetadataService.initialize(ENTITIES)
    
    if verbose:
        print(f"✅ Metadata loaded into MetadataService")


async def save_test_data(config_data: dict, verbose: bool = False) -> bool:
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
        
        # Process each entity factory directly
        for entity_name, factory_class in [('User', UserDataFactory), ('Account', AccountDataFactory)]:
            if verbose:
                print(f"  📝 Generating data for {entity_name}...")
            
            # Factory generates its own data with its own good/bad counts
            factory_class.generate_data()
            # Get all records from static test_scenarios
            all_scenarios = factory_class.test_scenarios
            valid_records = [record for record in all_scenarios if not ("bad_" in record.get('id', '') or "expired_" in record.get('id', '') or "multiple_errors" in record.get('id', ''))]
            invalid_records = [record for record in all_scenarios if ("bad_" in record.get('id', '') or "expired_" in record.get('id', '') or "multiple_errors" in record.get('id', ''))]
            all_records = valid_records + invalid_records
            
            if verbose:
                print(f"    Generated {len(valid_records)} valid + {len(invalid_records)} invalid records")
            
            all_entity_data[entity_name] = all_records
        
        # Step 2: Initialize metadata cache and apply metadata-driven field management
        # Metadata is now handled by MetadataService.initialize() above
        
        for entity_name, records in all_entity_data.items():
            if verbose:
                print(f"  🔧 Initializing metadata and applying field management for {entity_name}...")
            
            for record in records:
                apply_metadata_fields(record, entity_name.capitalize(), verbose)
        
        # Step 3: Initialize DB once, save all data, close DB once  
        db_type: str = config_data.get('database', '')
        db_uri: str = config_data.get('db_uri', '')
        db_name: str = config_data.get('db_name', '')
        
        await DatabaseFactory.initialize(db_type, db_uri, db_name)
        
        total_saved = 0
        for entity_name, records in all_entity_data.items():
            if verbose:
                print(f"  💾 Saving {len(records)} {entity_name} records to database...")
            
            saved_count = 0
            for i, record in enumerate(records):
                try:
                    data, count = await DatabaseFactory.create(entity_name, record, validate=False)
                    if count > 0:
                        saved_count += 1
                        if verbose:
                            print(f"      ✓ Created record {record.get('id', i+1)}")
                    else:
                        if verbose:
                            print(f"      ⚠️ Failed to create record {record.get('id', i+1)}")
                            
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


def apply_metadata_fields(record: Dict[str, Any], entity_name: str, verbose: bool = False) -> None:
    """
    Apply metadata-driven field management for any entity using MetadataService.
    Handles required, autogenerate, and autocreate datetime fields.
    """
    try:
        from datetime import datetime, timezone
        import uuid
        from app.services.metadata import MetadataService
        
        fields = MetadataService.fields(entity_name)
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