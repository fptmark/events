"""
Document CRUD operations with explicit parameters.
No dependency on RequestContext - can be used standalone.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from app.services.notify import Notification, Warning, Error
from app.db.core_manager import CoreManager
from app.db.exceptions import DocumentNotFound, DuplicateConstraintError, ModelNotFound
from app.services.metadata import MetadataService
from app.services.model import ModelService
from app.services.request_context import RequestContext
from app.config import Config
import app.models.utils as utils



class DocumentManager(ABC):
    """Document CRUD operations with clean, focused interface"""

    def __init__(self, database):
        """Initialize with database interface reference for cleaner access patterns"""
        self.database = database
    
    async def get_all(
        self,
        entity_type: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25,
        view_spec: Dict[str, Any] = {}
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of documents with explicit parameters.

        Args:
            entity_type: Entity type (e.g., "user", "account")
            sort: List of (field, direction) tuples, e.g., [("firstName", "asc")]
            filter: Filter conditions, e.g., {"status": "active", "age": {"$gte": 21}}
            page: Page number (1-based)
            pageSize: Number of items per page
            view_spec: View specification for field selection

        Returns:
            Tuple of (documents, total_count)
        """
        try:
            docs, count = await self._get_all_impl(entity_type, sort, filter, page, pageSize)

            if docs:
                # Get the model class for validation
                model_class = ModelService.get_model_class(entity_type)

                validate = Config.validation(True)
                metadata = MetadataService.get(entity_type)
                unique_constraints = metadata.get('uniques', []) if metadata else []

                # Process each document
                for i in range(len(docs)):
                    docs[i] = await self._normalize_document(entity_type, docs[i], model_class, view_spec, unique_constraints, validate)

            return docs, count
        except Exception as e:
            Notification.error(Error.DATABASE, f"Database get_all error: {str(e)}")
            return [], 0

    @abstractmethod
    async def _get_all_impl(
        self,
        entity_type: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Database-specific implementation of get_all"""
        pass
    
    async def get(
        self,
        entity_type: str,
        id: str,
        view_spec: Dict[str, Any] = {}
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get single document by ID.

        Args:
            id: Document ID
            entity_type: Entity type (e.g., "user", "account")
            view_spec: View specification for field selection

        Returns:
            Tuple of (document, count) where count is 1 if found, 0 if not found
        """
        try:
            doc, count = await self._get_impl(id, entity_type)
            if count > 0 and doc:
                model_class = ModelService.get_model_class(entity_type)
                validate = Config.validation(False)
                metadata = MetadataService.get(entity_type)
                unique_constraints = metadata.get('uniques', []) if metadata else []

                doc = await self._normalize_document(entity_type, doc, model_class, view_spec, unique_constraints, validate)
            return doc, count
        except DocumentNotFound as e:
            msg = str(e.message) if e.message else str(e.error)
            Notification.warning(Warning.NOT_FOUND, message=msg, entity_type=entity_type, entity_id=id)
            return {}, 0
        except Exception as e:
            Notification.error(Error.DATABASE, f"Database get error: {str(e)}")
            return {}, 0

    async def _normalize_document(self, entity_type: str, doc: Dict[str, Any], model_class: Any, view_spec: Dict[str, Any], 
                                  unique_constraints : List[Any], validate: bool) -> Dict[str, Any]:
        """Normalize document by extracting internal id field and renaming to 'id'"""
        try:
            doc = self._remove_sub_objects(entity_type, doc)    # should not be there anyway

            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(model_class, doc, entity_type)

            if validate:
                await utils.validate_uniques(entity_type, doc, unique_constraints, None)

            # Populate view data if requested and validate fks
            if view_spec is None:
                view_spec = {}
            await utils.process_fks(entity_type, doc, validate, view_spec)

        except DocumentNotFound as e:
            msg = str(e.message) if e.message else str(e.error)
            Notification.warning(Warning.NOT_FOUND, message=msg, entity_type=entity_type, entity_id=doc.get('id', ''))
            return {}
        except Exception as e:
                Notification.error(Error.DATABASE, f"Database get error: {str(e)}")
                return {}
        
        # move internal id to 'id' field
        core = self._get_core_manager()
        id = doc.pop(core.id_field, None)
        out_doc: Dict[str, Any] = {'id': id, **doc}

        return out_doc or {}

                                    
    @abstractmethod
    async def _get_impl(
        self,
        id: str,
        entity_type: str
    ) -> Tuple[Dict[str, Any], int]:
        """Database-specific implementation of get"""
        pass
    
    async def _save_document(
        self,
        entity_type: str,
        data: Dict[str, Any],
        is_update: bool = False
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create new document. If data contains 'id', use it as _id, otherwise auto-generate.

        Args:
            entity_type: Entity type (e.g., "user", "account")
            data: Document data to save
            validate: Unused parameter (validation handled at model layer)

        Returns:
            Tuple of (saved_document, count) where count is 1 if created, 0 if failed
        """
        # remove the id from the data and pass it separately
        orig = data.copy()
        id = (data.pop('id', '') or '').strip()

        # Validate input data if validation is enabled.  it should only be disabled for writing test data (?novalidate param)
        if not RequestContext.novalidate:
            model_class = ModelService.get_model_class(entity_type)   #self._get_model_class(entity_type)
            utils.validate_model(model_class, data, entity_type)

        # Check if document exists for update
        if is_update:
            if not id:
                Notification.error(Error.REQUEST, "Missing 'id' field or value for update operation")
                return orig, 0
            doc, count = await self.get(entity_type, id)
            if count == 0:
                Notification.error(Error.REQUEST, "Document to update not found using id")
                return orig, 0

        # Validate unique constraints from metadata (only for databases without native support)
        metadata = MetadataService.get(entity_type)
        unique_constraints = metadata.get('uniques', []) if metadata else []
        # Use database interface for database-level methods
        if unique_constraints and not self.database.supports_native_indexes():
            exclude_id = id if is_update else None
            await utils.validate_uniques(entity_type, data, unique_constraints, exclude_id)   # raise on failure

        # Process foreign keys (?view)
        result = await utils.process_fks(entity_type, data, True)
        if isinstance(result, bool) and result:
            # Prepare data for database storage (database-specific)
            prepared_data = self._prepare_datetime_fields(entity_type, data)

            # Remove any sub-objects so we don't store them in the db
            prepared_data = self._remove_sub_objects(entity_type, prepared_data)

            # Save in database (database-specific implementation)
            try:
                if is_update:
                    doc = await self._update_impl(entity_type, id, prepared_data)
                else:
                    doc = await self._create_impl(entity_type, id, prepared_data)
                return doc, 1
            except DuplicateConstraintError as e:
                Notification.error(Error.DATABASE, f"Duplicate key error: {str(e)}")
            except Exception as e:
                operation = "update" if is_update else "create"
                Notification.error(Error.DATABASE, f"{operation} error: {str(e)}")
        else:
            operation = "update" if is_update else "create"
            Notification.error(Error.REQUEST, f"Foreign key validation of {result} failed for {operation}")
        return {}, 0
        
    async def create(
        self,
        entity_type: str,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """Create new document. If data contains 'id', use it as _id, otherwise auto-generate."""
        return await self._save_document(entity_type, data, is_update=False)

    @abstractmethod
    async def _create_impl(self, entity_type: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    async def update(
        self,
        entity_type: str,
        data: Dict[str, Any],
        validate: bool = True
    ) -> Tuple[Dict[str, Any], int]:
        """Update existing document by id. Fails if document doesn't exist."""
        return await self._save_document(entity_type, data, is_update=True)

    @abstractmethod  
    async def _update_impl(self, entity_type: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def delete(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """
        Delete document by ID.

        Args:
            id: Document ID to delete
            entity_type: Entity type (e.g., "user", "account")

        Returns:
            Tuple of (deleted_document, count) where count is 1 if deleted, 0 if not found
        """
        return await self._delete_impl(id, entity_type)

    @abstractmethod
    async def _delete_impl(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Database-specific implementation of delete"""
        pass
    
    # @abstractmethod
    # async def _validate_document_exists_for_update(self, entity_type: str, id: str) -> bool:
    #     """
    #     Validate that document exists for update operations (database-specific).
    #     Should add not_found_warning and return False if document doesn't exist.
        
    #     Returns:
    #         True if document exists, False if not found (with warning added)
    #     """
    #     pass
    
    @abstractmethod
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance from the concrete implementation"""
        pass

    # Abstract methods for database-specific logic
    @abstractmethod
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for database storage (database-specific)"""
        pass
    
    @abstractmethod
    def _convert_filter_values(self, filters: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Convert filter values to database-appropriate types (database-specific)"""
        pass
        
    @abstractmethod
    async def _validate_unique_constraints(
        self, 
        entity_type: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints (database-specific implementation)
        
        Args:
            entity_type: Entity type
            data: Document data to validate
            unique_constraints: List of unique constraint field groups
            exclude_id: ID to exclude from validation (for updates)
        
        Returns:
            True if constraints are valid, False if constraint violations detected
        """
        pass

    def _remove_sub_objects(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any sub-objects from the data before storing in the database"""
        # look for any <field>id that are ObjectId types and remove the corresponding <field> sub-object
        cleaned_data = data.copy()
        for field in data:
            if MetadataService.get(entity_type, field + "id", 'type') == 'ObjectId':
                cleaned_data.pop(field)

        return cleaned_data

