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
from . import get_data_factory, DATA_FACTORIES


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
            factory = factory_class()
            valid_records, invalid_records = factory.generate_data()
            all_records = valid_records + invalid_records
            
            if verbose:
                print(f"    Generated {len(valid_records)} valid + {len(invalid_records)} invalid records")
            
            all_entity_data[entity_name] = all_records
        
        # Step 2: Apply metadata-driven field management to each entity's data
        for entity_name, records in all_entity_data.items():
            if verbose:
                print(f"  🔧 Applying metadata field management for {entity_name}...")
            
            model_class = utils.get_model_class(entity_name.capitalize())
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