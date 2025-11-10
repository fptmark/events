"""
Hook service for pre/post entity get/get_all/create/update/delete actions
"""

from typing import List, Tuple, Any, Dict, Union
import inspect
from app.core.metadata import MetadataService
from app.core.request_context import RequestContext
from app.core.notify import Notification, HTTP
from app.services.services import ServiceManager


class HookService:

    _hooks: List[Tuple[str, bool, str, Any]] = []

    _known_operations: List[str] = ['create', 'update', 'delete', 'get', 'get_all']

    # Each register may have an empty entity which means apply to all
    # operations must contain create|update|delete|get|get_all
    @staticmethod
    def register(entity_name: str, preflight: bool, operations: List[str], callback: Any):
        assert( entity_name )
        for operation in operations:
            if operation in HookService._known_operations:
                HookService._hooks.append((entity_name, preflight, operation, callback))
            else:
                print(f"Bad registation option {operation}.  Must be in {HookService._known_operations}")

    @staticmethod
    def deregister(entity_name: str, preflight: bool, operation: str):
        assert( entity_name )
        for i, (hook_entity_name, hook_preflight, hook_operation, _) in enumerate(HookService._hooks):
            if entity_name == hook_entity_name and preflight == hook_preflight and operation == hook_operation:
                del HookService._hooks[i]
                break

    @staticmethod
    async def call_preflight(entity_name: str, operation: str, **context) -> bool:
        """
        Call preflight hook before operation.

        Args:
            entity_name: Entity being operated on (e.g., "User")
            operation: Operation being performed (e.g., "create", "update")
            **context: Flexible context passed to hook (e.g., request_data, user, filters)

        Returns:
            bool: True to proceed with operation, False to abort
        """
        assert( entity_name and operation )
        for hook_entity_name, hook_preflight, hook_operation, callback in HookService._hooks:
            if entity_name == hook_entity_name and hook_preflight and operation == hook_operation:
                # Check if callback is async before calling
                if inspect.iscoroutinefunction(callback):
                    return await callback(**context)
                else:
                    return callback(**context)

        # No hook found - default: allow operation to proceed
        return True

    @staticmethod
    async def call_postflight(entity_name: str, operation: str, docs: List[Dict[str, Any]], doc_count: int, **context) -> Tuple[List[Dict[str, Any]], int]:
        """
        Call postflight hook after operation.

        Args:
            entity_name: Entity being operated on (e.g., "User")
            operation: Operation being performed (e.g., "create", "update")
            docs: Result documents from operation
            doc_count: Number of documents

        Returns:
            Tuple[List[Dict[str, Any]], int]: Potentially modified (docs, doc_count)
        """
        assert( entity_name and operation )
        for hook_entity_name, hook_preflight, hook_operation, callback in HookService._hooks:
            if entity_name == hook_entity_name and not hook_preflight and operation == hook_operation:
                # Check if callback is async before calling
                if inspect.iscoroutinefunction(callback):
                    return await callback(docs, doc_count, **context)
                else:
                    return callback(docs, doc_count, **context)

        # No hook found - default: return unchanged
        return docs, doc_count