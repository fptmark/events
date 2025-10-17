"""
Document CRUD operations with explicit parameters.
No dependency on RequestContext - can be used standalone.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import warnings as python_warnings
from pydantic import ValidationError as PydanticValidationError

from app.services.notify import Notification, Warning, HTTP
from app.db.core_manager import CoreManager
from app.exceptions import DocumentNotFound, DuplicateConstraintError
from app.services.metadata import MetadataService
from app.services.model import ModelService
from app.services.request_context import RequestContext
from app.config import Config

class DocumentManager(ABC):
    """Document CRUD operations with clean, focused interface"""

    def __init__(self, database):
        """Initialize with database interface reference for cleaner access patterns"""
        self.database = database
    
    async def get_all(
        self,
        entity: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25,
        view_spec: Dict[str, Any] = {}
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of documents with explicit parameters.

        Args:
            entity: Entity type (e.g., "user", "account")
            sort: List of (field, direction) tuples, e.g., [("firstName", "asc")]
            filter: Filter conditions, e.g., {"status": "active", "age": {"$gte": 21}}
            page: Page number (1-based)
            pageSize: Number of items per page
            view_spec: View specification for field selection

        Returns:
            Tuple of (documents, total_count)
        """
        try:
            docs, count = await self._get_all_impl(entity, sort, filter, page, pageSize)

            if docs:
                # Get the model class for validation
                model_class = ModelService.get_model_class(entity)

                validate = Config.validation(True)
                metadata = MetadataService.get(entity)
                unique_constraints = metadata.get('uniques', []) if metadata else []

                # Process each document
                for i in range(len(docs)):
                    docs[i] = await self._normalize_document(entity, docs[i], model_class, view_spec, unique_constraints, validate)

            return docs, count
        except Exception as e:
            Notification.error(HTTP.INTERNAL_ERROR, f"Database get_all error: {str(e)}")
            raise  # Unreachable but satisfies type checker

    @abstractmethod
    async def _get_all_impl(
        self,
        entity: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Database-specific implementation of get_all"""
        pass
    
    async def get(
        self,
        entity: str,
        id: str,
        view_spec: Dict[str, Any] = {},
        top_level: bool = True
    ) -> Tuple[Dict[str, Any], int, Optional[BaseException]]:
        """
        Get single document by ID.

        Args:
            id: Document ID
            entity: Entity type (e.g., "user", "account")
            view_spec: View specification for field selection

        Returns:
            Tuple of (document, count) where count is 1 if found, 0 if not found
        """
        try:
            doc, count = await self._get_impl(id, entity)
            if count > 0 and doc:
                model_class = ModelService.get_model_class(entity)
                validate = Config.validation(False)
                metadata = MetadataService.get(entity)
                unique_constraints = metadata.get('uniques', []) if metadata else []

                doc = await self._normalize_document(entity, doc, model_class, view_spec, unique_constraints, validate)
            return doc, count, None
        except DocumentNotFound as e:
            if top_level:
                msg = str(e.message) if e.message else str(e.error)
                Notification.warning(Warning.NOT_FOUND, message=msg, entity=entity, entity_id=id)
                Notification.error(HTTP.NOT_FOUND, msg, entity=entity)
            else:
                return {}, 0, e
            raise  # Unreachable
        except Exception as e:
            if top_level:
                Notification.error(HTTP.INTERNAL_ERROR, f"Database get error: {str(e)}")
            else:
                return {}, 0, e
            raise  # Unreachable

    async def _normalize_document(self, entity: str, doc: Dict[str, Any], model_class: Any, view_spec: Dict[str, Any], 
                                  unique_constraints : List[Any], validate: bool) -> Dict[str, Any]:
        """Normalize document by extracting internal id field and renaming to 'id'"""
        try:
            # make sure the id is in the right plae
            core = self._get_core_manager()
            id = doc.pop(core.id_field, None)
            the_doc: Dict[str, Any] = {'id': id, **doc} # ensure id is first field

            the_doc = self._remove_sub_objects(entity, the_doc)    # should not be there anyway

            # Always run Pydantic validation (required fields, types, ranges)
            validate_model(model_class, the_doc, entity)

            if validate:
                await validate_uniques(entity, the_doc, unique_constraints, None)

            # Populate view data if requested and validate fks
            # if view_spec is None:
            #     view_spec = {}
            await process_fks(entity, the_doc, validate, view_spec)

        except DocumentNotFound as e:
            msg = str(e.message) if e.message else str(e.error)
            Notification.warning(Warning.NOT_FOUND, message=msg, entity=entity, entity_id=id)
            Notification.error(HTTP.NOT_FOUND, msg, entity=entity)
            raise  # Unreachable
        except Exception as e:
            Notification.error(HTTP.INTERNAL_ERROR, f"Database retrieve error: {str(e)}")
            raise  # Unreachable

        return the_doc or {}

                                    
    @abstractmethod
    async def _get_impl(
        self,
        id: str,
        entity: str,
    ) -> Tuple[Dict[str, Any], int]:
        """Database-specific implementation of get"""
        pass
    
    async def _save_document(
        self,
        entity: str,
        data: Dict[str, Any],
        is_update: bool = False
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create new document. If data contains 'id', use it as _id, otherwise auto-generate.

        Args:
            entity: Entity type (e.g., "user", "account")
            data: Document data to save
            validate: Unused parameter (validation handled at model layer)

        Returns:
            Tuple of (saved_document, count) where count is 1 if created, 0 if failed
        """
        # remove the id from the data and pass it separately
        # orig = data.copy()
        id = (data.pop('id', '') or '').strip()

        # Validate input data if validation is enabled.  it should only be disabled for writing test data (?novalidate param)
        # if not RequestContext.novalidate:    - DEPRECATED - always validate
        model_class = ModelService.get_model_class(entity)   #self._get_model_class(entity)
        validate_model(model_class, data, entity)

        # Check if document exists for update
        if is_update:
            if not id:
                Notification.error(HTTP.BAD_REQUEST, "Missing 'id' field or value for update operation", entity=entity, field="id")
                raise  # Unreachable
            try:
                doc, count = await self._get_impl(id, entity)  # only check for existance - no validation
                if count == 0:
                    Notification.error(HTTP.NOT_FOUND, f"Document to update not found: {id}", entity=entity)
            except DocumentNotFound:
                Notification.error(HTTP.NOT_FOUND, f"Document to update not found: {id}", entity=entity)
            except:
                Notification.error(HTTP.INTERNAL_ERROR, f"Document error in update: {id}", entity=entity)

        # Validate unique constraints from metadata (only for databases without native support)
        metadata = MetadataService.get(entity)
        unique_constraints = metadata.get('uniques', []) if metadata else []
        # Use database interface for database-level methods
        if unique_constraints and not self.database.supports_native_indexes():
            exclude_id = id if is_update else None
            await validate_uniques(entity, data, unique_constraints, exclude_id)   # raise on failure

        # Process foreign keys (?view)
        result = await process_fks(entity, data, True)
        if isinstance(result, bool) and result:
            # Prepare data for database storage (database-specific)
            prepared_data = self._prepare_datetime_fields(entity, data)

            # Remove any sub-objects so we don't store them in the db
            prepared_data = self._remove_sub_objects(entity, prepared_data)

            # Save in database (database-specific implementation)
            try:
                if is_update:
                    doc = await self._update_impl(entity, id, prepared_data)
                    return {'id': id, **doc}, 1
                else:
                    doc = await self._create_impl(entity, id, prepared_data)
                    return doc, 1
            except DuplicateConstraintError as e:
                Notification.error(HTTP.CONFLICT, f"Duplicate key error: {str(e)}")
                raise  # Unreachable
            except Exception as e:
                operation = "update" if is_update else "create"
                Notification.error(HTTP.INTERNAL_ERROR, f"{operation} error: {str(e)}")
                raise  # Unreachable
        else:
            operation = "update" if is_update else "create"
            Notification.error(HTTP.UNPROCESSABLE, f"Foreign key validation of {result} failed for {operation}")
            raise  # Unreachable
        
    async def create(
        self,
        entity: str,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """Create new document. If data contains 'id', use it as _id, otherwise auto-generate."""
        return await self._save_document(entity, data, is_update=False)

    @abstractmethod
    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    async def update(
        self,
        entity: str,
        id: str,
        data: Dict[str, Any],
        validate: bool = True
    ) -> Tuple[Dict[str, Any], int]:
        """Update existing document by id. Fails if document doesn't exist."""
        data['id'] = id  # Ensure id parameter takes precedence
        return await self._save_document(entity, data, is_update=True)

    @abstractmethod  
    async def _update_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def delete(self, id: str, entity: str) -> Tuple[Dict[str, Any], int]:
        """
        Delete document by ID. Idempotent - returns success even if already deleted.

        Args:
            id: Document ID to delete
            entity: Entity type (e.g., "user", "account")

        Returns:
            Tuple of (deleted_document, count) where count is 1 if deleted, 0 if not found
        """
        try:
            return await self._delete_impl(id, entity)
        except DocumentNotFound:
            # Idempotent DELETE: already gone = success
            return {}, 0

    @abstractmethod
    async def _delete_impl(self, id: str, entity: str) -> Tuple[Dict[str, Any], int]:
        """Database-specific implementation of delete"""
        pass
    
    @abstractmethod
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance from the concrete implementation"""
        pass

    # Abstract methods for database-specific logic
    @abstractmethod
    def _prepare_datetime_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for database storage (database-specific)"""
        pass
    
    @abstractmethod
    def _convert_filter_values(self, filters: Dict[str, Any], entity: str) -> Dict[str, Any]:
        """Convert filter values to database-appropriate types (database-specific)"""
        pass
        
    @abstractmethod
    async def _validate_unique_constraints(
        self, 
        entity: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints (database-specific implementation)
        
        Args:
            entity: Entity type
            data: Document data to validate
            unique_constraints: List of unique constraint field groups
            exclude_id: ID to exclude from validation (for updates)
        
        Returns:
            True if constraints are valid, False if constraint violations detected
        """
        pass

    def _remove_sub_objects(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any sub-objects from the data before storing in the database"""
        # look for any <field>id that are ObjectId types and remove the corresponding <field> sub-object
        cleaned_data = data.copy()
        for field in data:
            if MetadataService.get(entity, field + "id", 'type') == 'ObjectId':
                cleaned_data.pop(field)

        return cleaned_data


async def validate_uniques(entity: str, data: Dict[str, Any], unique_constraints: List[List[str]], exclude_id: Optional[str] = None) -> None:
    """
    Worker function: Validate unique constraints using database-specific implementation.
    Always enforced regardless of validation settings - unique constraints are business rules.
    
    Args:
        entity: Entity type to validate
        data: Entity data dictionary
        unique_constraints: List of unique constraint field groups
        exclude_id: ID to exclude from validation (for updates)
    
    Raises:
        ValidationError: If any unique constraints are violated
    """
    from app.db.factory import DatabaseFactory
    
    db = DatabaseFactory.get_instance()
    constraint_success = await db.documents._validate_unique_constraints(
        entity=entity,
        data=data,
        unique_constraints=unique_constraints,
        exclude_id=exclude_id
    )
    
    # For MongoDB, this will always be True (relies on native database constraints)
    # For Elasticsearch, this returns False if synthetic validation finds duplicates
    if not constraint_success:
        raise DuplicateConstraintError(f"Unique constraint violation for {entity}")
        # Note: MongoDB will throw DuplicateKeyError, Elasticsearch handles in _validate_unique_constraints


def validate_model(cls, data: Dict[str, Any], entity_name: str):
    """
    Worker function: Validate data with Pydantic and convert errors to notifications.
    Returns the validated instance or unvalidated instance if validation fails.
    
    This handles basic model validation:
    - Enum validation (gender must be 'male', 'female', 'other')
    - Range validation (netWorth >= 0) 
    - String validation (length, format, etc.)
    - Type validation (int, float, bool, etc.)
    
    This does NOT handle FK validation - that's separate.
    """
    try:
        return cls.model_validate(data)
    except PydanticValidationError as e:
        entity_id = data.get('id', 'unknown')
        for error in e.errors():
            field = str(error['loc'][-1]) if error.get('loc') else 'unknown'
            Notification.warning(Warning.DATA_VALIDATION, "Validation error", entity=entity_name, entity_id=entity_id, field=field, value=error.get('msg', 'Validation error'))
            success = False
        # Return unvalidated instance so API can continue
        return cls.model_construct(**data)


async def process_fks(entity: str, data: Dict[str, Any], validate: bool, view_spec: Dict[str, Any] = {}) -> Any:
    """
    Unified FK processing: validation + view population in single pass.
    Only makes DB calls when data is actually needed.
    return bad FK name if validate mode or True
    """
    
    fk_data = None
    entity_id = data.get('id', 'new')   # use 'new' if no id on create
    for field, field_meta in MetadataService.fields(entity).items():
        # process every FK field if validating OR if it's in the view spec
        if field_meta.get('type') == 'ObjectId' and len(field) > 2:
            fk_name = field[:-2]  # Remove 'Id' suffix to get FK entity name

            if validate or fk_name.lower() in view_spec.keys():
                fk_entity = MetadataService.get_proper_name(fk_name)
                fk_data = {"exists": False}
                fk_field_id = data.get(field, None)
                
                if fk_field_id:
                    fk_cls = ModelService.get_model_class(fk_entity)
                    
                    if fk_cls:
                        # Fetch FK record
                        with Notification.suppress_warnings():  # suppress warnings when fetching a fk as the code below has a better warning (it includes the offending field)
                            related_data, count, excpt = await fk_cls.get(fk_field_id, None, False)
                        if count == 0:
                            # FK record not found - validation warning if validating
                            Notification.error(HTTP.UNPROCESSABLE, "Referenced ID does not exist", entity=entity, field=field)
                        # if there is more than one fk record, something is very wrong
                        elif count == 1:
                            fk_data["exists"] = True
                            
                            # Populate requested fields if view_spec provided
                            if fk_entity.lower() in view_spec.keys():
                                # Handle case-insensitive field matching
                                field_map = {k.lower(): k for k in related_data.keys()}
                                
                                for field in view_spec[fk_entity.lower()] or []:
                                    if field in related_data:
                                        fk_data[field] = related_data[field]
                                    elif field.lower() in field_map:
                                        actual_field = field_map[field.lower()]
                                        fk_data[actual_field] = related_data[actual_field]
                                    else :
                                        attrs = MetadataService.get(fk_entity, field)
                                        if 'required' in attrs and attrs['required'].lower() == 'true':
                                            Notification.warning(Warning.BAD_NAME, "Field not found in related entity", entity=entity, entity_id=entity_id, field=field)
                                        
                        else:
                            # Multiple records - data integrity issue
                            Notification.warning(Warning.DATA_VALIDATION, "Multiple FK records found. Data integrity issue?", entity=entity, entity_id=entity_id, field=field, value=fk_field_id)
                            
                    else:
                        Notification.warning(Warning.NOT_FOUND, "FK entity does not exist", entity=entity, entity_id=entity_id, field=field, value=fk_entity)
                else:
                    # Invalid entity class or missing ID - validation warning if validating and required or entity in view spec
                    if (validate and field_meta.get('required', False)) or fk_name.lower() in view_spec.keys():
                        Notification.warning(Warning.MISSING, "Missing fk ID", entity=entity, entity_id=entity_id, field=field)
                
                # Set FK field data (inside the loop for each FK)
                data[fk_name] = fk_data  

                # If validating and a specified FK does not exist, return False
                if validate and not fk_data.get("exists"):
                    return fk_name  # FK validation failed
    return True  # All FKs valid or no validation needed