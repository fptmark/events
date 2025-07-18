from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
import logging
from contextvars import ContextVar


def _default_timestamp() -> datetime:
    """Default timestamp factory"""
    return datetime.now(timezone.utc)


class NotificationLevel(Enum):
    """Notification severity levels"""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class NotificationType(Enum):
    """Types of notifications"""
    VALIDATION = "validation"
    DATABASE = "database"
    BUSINESS = "business"
    SYSTEM = "system"
    SECURITY = "security"


@dataclass
class NotificationDetail:
    """Single notification detail with hierarchical support"""
    message: str
    level: NotificationLevel
    type: NotificationType
    entity: Optional[str] = None
    operation: Optional[str] = None
    field_name: Optional[str] = None
    value: Optional[Any] = None
    entity_id: Optional[str] = None  # Added for bulk operations
    timestamp: datetime = dataclass_field(default_factory=_default_timestamp)
    details: List['NotificationDetail'] = dataclass_field(default_factory=list)

    def add_detail(self, message: str, level: Optional[NotificationLevel] = None, 
                   type: Optional[NotificationType] = None, **kwargs) -> None:
        """Add a child detail to this notification"""
        detail = NotificationDetail(
            message=message,
            level=level or self.level,
            type=type or self.type,
            entity=kwargs.get('entity', self.entity),
            operation=kwargs.get('operation', self.operation),
            field_name=kwargs.get('field_name'),
            value=kwargs.get('value'),
            entity_id=kwargs.get('entity_id')
        )
        self.details.append(detail)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "message": self.message,
            "level": self.level.value,
            "type": self.type.value,
            "entity": self.entity,
            "operation": self.operation,
            "field": self.field_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "details": [d.to_dict() for d in self.details] if self.details else []
        }
        
        # Include entity_id only if it's provided (for bulk operations)
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
            
        return result


class SimpleNotificationCollection:
    """Simplified notification collection for REST operations"""
    
    def __init__(self, entity: Optional[str] = None, operation: Optional[str] = None):
        self.entity = entity
        self.operation = operation
        self.notifications: List[NotificationDetail] = []
        
    def add(self, message: str, level: NotificationLevel, type: NotificationType, 
            entity: Optional[str] = None, operation: Optional[str] = None,
            field_name: Optional[str] = None, value: Optional[Any] = None,
            entity_id: Optional[str] = None) -> NotificationDetail:
        """Add a notification and return it for potential detail addition"""
        notification = NotificationDetail(
            message=message,
            level=level,
            type=type,
            entity=entity or self.entity,
            operation=operation or self.operation,
            field_name=field_name,
            value=value,
            entity_id=entity_id
        )
        self.notifications.append(notification)
        
        # Log to console with details
        self._log_notification(notification)
        
        return notification

    def success(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
        """Add success notification"""
        return self.add(message, NotificationLevel.SUCCESS, type, **kwargs)

    def info(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
        """Add info notification"""
        return self.add(message, NotificationLevel.INFO, type, **kwargs)

    def warning(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
        """Add warning notification"""
        return self.add(message, NotificationLevel.WARNING, type, **kwargs)

    def error(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
        """Add error notification"""
        return self.add(message, NotificationLevel.ERROR, type, **kwargs)

    def validation_error(self, message: str, field_name: Optional[str] = None, 
                        value: Optional[Any] = None, entity_id: Optional[str] = None, **kwargs) -> NotificationDetail:
        """Add validation error with field details"""
        return self.error(message, NotificationType.VALIDATION, 
                         field_name=field_name, value=value, entity_id=entity_id, **kwargs)

    def database_error(self, message: str, **kwargs) -> NotificationDetail:
        """Add database error"""
        return self.error(message, NotificationType.DATABASE, **kwargs)

    def has_errors(self) -> bool:
        """Check if collection contains any errors"""
        return any(n.level == NotificationLevel.ERROR for n in self.notifications)

    def has_warnings(self) -> bool:
        """Check if collection contains any warnings"""
        return any(n.level == NotificationLevel.WARNING for n in self.notifications)

    def get_summary(self) -> Dict[str, int]:
        """Get summary counts by level"""
        summary = {level.value: 0 for level in NotificationLevel}
        for notification in self.notifications:
            summary[notification.level.value] += 1
        return summary

    def get_primary_message(self) -> tuple[Optional[str], Optional[str]]:
        """Get primary display message prioritizing errors > warnings > success"""
        errors = [n for n in self.notifications if n.level == NotificationLevel.ERROR]
        warnings = [n for n in self.notifications if n.level == NotificationLevel.WARNING]
        successes = [n for n in self.notifications if n.level == NotificationLevel.SUCCESS]
        
        if errors:
            return errors[0].message, "error"
        elif warnings:
            return warnings[0].message, "warning"
        elif successes:
            for success in successes:
                if any(action in success.message.lower() 
                      for action in ['created', 'updated', 'deleted', 'saved']):
                    return success.message, "success"
        
        return None, None

    def to_response(self, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert to standard API response format"""
        message, level = self.get_primary_message()
        
        response = {
            "data": data,
            "message": message,
            "level": level
        }
        
        # Add metadata if provided
        if metadata:
            response["metadata"] = metadata
        
        # Include notifications if there are multiple or if there are details
        if len(self.notifications) > 1 or any(n.details for n in self.notifications):
            response["notifications"] = [n.to_dict() for n in self.notifications]
            response["summary"] = self.get_summary()
        
        return response

    def to_entity_grouped_response(self, data: Any = None, is_bulk: bool = False) -> Dict[str, Any]:
        """Convert to entity-grouped API response format"""
        
        # Group notifications by entity_id
        entity_notifications = self._group_by_entity()
        
        # Determine overall status
        status = self._determine_status(entity_notifications, data, is_bulk)
        
        # Only wrap in array for bulk operations
        if is_bulk and data is not None and not isinstance(data, list):
            data = [data]
        
        response = {
            "status": status,
            "data": data
        }
        
        # Only include notifications if there are issues
        if entity_notifications:
            response["notifications"] = entity_notifications
        
        # Include summary if there are notifications or it's bulk
        if entity_notifications or is_bulk:
            response["summary"] = self._get_entity_summary(entity_notifications, data)
            
        return response

    def _group_by_entity(self) -> Dict[str, Dict[str, Any]]:
        """Group notifications by entity_id"""
        grouped: Dict[str, Dict[str, Any]] = {}
        
        for notification in self.notifications:
            entity_id = notification.entity_id if notification.entity_id is not None else "null"
            
            if entity_id not in grouped:
                grouped[entity_id] = {
                    "entity_id": notification.entity_id,
                    "entity_type": notification.entity or "Unknown",
                    "status": "success",
                    "errors": [],
                    "warnings": []
                }
            
            # Convert notification to simplified format
            notif_dict = {
                "type": notification.type.value,
                "severity": notification.level.value,
                "message": notification.message
            }
            if notification.field_name:
                notif_dict["field"] = notification.field_name
            if notification.value is not None:
                notif_dict["value"] = notification.value
                
            # Add to appropriate list and update entity status
            if notification.level == NotificationLevel.ERROR:
                grouped[entity_id]["errors"].append(notif_dict)
                grouped[entity_id]["status"] = "failed"
            elif notification.level == NotificationLevel.WARNING:
                grouped[entity_id]["warnings"].append(notif_dict)
                if grouped[entity_id]["status"] == "success":
                    grouped[entity_id]["status"] = "warning"
        
        return grouped

    def _determine_status(self, entity_notifications: Dict[str, Dict], data: Any, is_bulk: bool) -> str:
        """Determine overall response status based on entity notifications"""
        
        if not entity_notifications:
            return "perfect"
        
        has_failures = any(entity["status"] == "failed" for entity in entity_notifications.values())
        
        if is_bulk:
            # For bulk operations, if we have any data, it's completed even with failures
            if data is not None and (isinstance(data, list) and len(data) > 0 or data):
                return "completed"
            else:
                return "failed"
        else:
            # For single entity operations
            if has_failures:
                return "failed"
            else:
                # Check if we have warnings
                has_warnings = any(entity["status"] == "warning" for entity in entity_notifications.values())
                return "warning" if has_warnings else "completed"

    def _get_entity_summary(self, entity_notifications: Dict[str, Dict], data: Any) -> Dict[str, Any]:
        """Get summary counts based on entity notifications"""
        
        # Count individual notifications and entities by status
        perfect_entities = 0
        warning_entities = 0
        error_entities = 0
        total_warnings = 0
        total_errors = 0
        
        for entity in entity_notifications.values():
            if entity["status"] == "failed":
                error_entities += 1
                total_errors += len(entity["errors"])
                total_warnings += len(entity["warnings"])
            elif entity["status"] == "warning":
                warning_entities += 1
                total_warnings += len(entity["warnings"])
            else:
                perfect_entities += 1
        
        # Calculate total entities - distinguish between single entity (dict) and bulk (list)
        if data is not None:
            if isinstance(data, list):
                total_from_data = len(data)  # Bulk operation - count array items
            else:
                total_from_data = 1  # Single entity operation - count as 1
        else:
            total_from_data = 0
            
        # Total is either from data + failed entities, or from notifications
        total_entities = max(total_from_data + error_entities, len(entity_notifications))
        
        # If no notifications, all returned entities are perfect
        if not entity_notifications:
            perfect_entities = total_entities
        
        # Calculate successfully processed entities (only perfect, no warnings)
        successful_entities = perfect_entities
        
        return {
            "total_entities": total_entities,
            "perfect": perfect_entities,
            "successful": successful_entities,
            "warnings": total_warnings,
            "errors": total_errors
        }

    def _log_notification(self, notification: NotificationDetail, indent: int = 0) -> None:
        """Log notification and its details to console"""
        log_level_map = {
            NotificationLevel.SUCCESS: logging.INFO,
            NotificationLevel.INFO: logging.INFO,
            NotificationLevel.WARNING: logging.WARNING,
            NotificationLevel.ERROR: logging.ERROR
        }
        
        # Build unified format: [WARNING] User:687800bc55017d54db8e6042 [validation] password="<current_value>" String should have at least 8 characters
        prefix = "  " * indent
        
        # Entity part with ID
        if notification.entity and notification.entity_id:
            entity_part = f"{notification.entity}:{notification.entity_id}"
        elif notification.entity:
            entity_part = notification.entity
        else:
            entity_part = "System"
        
        # Field part with value
        field_part = ""
        if notification.field_name:
            if notification.value is not None:
                field_part = f"{notification.field_name}=\"{notification.value}\" "
            else:
                field_part = f"{notification.field_name}=\"\" "
        
        # Build final log message
        log_msg = f"{prefix}[{notification.level.value.upper()}] {entity_part} [{notification.type.value}] {field_part}{notification.message}"
        
        logging.log(log_level_map[notification.level], log_msg)
        
        # Log details with increased indentation
        for detail in notification.details:
            self._log_notification(detail, indent + 1)

# Context variable for current notification collection
_current_notifications: ContextVar[Optional[SimpleNotificationCollection]] = ContextVar(
    'current_notifications', default=None
)


def start_notifications(entity: Optional[str] = None, operation: Optional[str] = None) -> SimpleNotificationCollection:
    """Start a new notification collection for the current context"""
    collection = SimpleNotificationCollection(entity=entity, operation=operation)
    _current_notifications.set(collection)
    return collection


def get_notifications() -> SimpleNotificationCollection:
    """Get the current notification collection, creating one if needed"""
    collection = _current_notifications.get()
    if collection is None:
        collection = start_notifications()
    return collection


def end_notifications() -> SimpleNotificationCollection:
    """End the current notification collection and return it"""
    collection = get_notifications()
    _current_notifications.set(None)
    return collection


# Convenience functions for adding notifications
def notify_success(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
    """Add success notification to current collection"""
    return get_notifications().success(message, type, **kwargs)


def notify_info(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
    """Add info notification to current collection"""
    return get_notifications().info(message, type, **kwargs)


def notify_warning(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
    """Add warning notification to current collection"""
    return get_notifications().warning(message, type, **kwargs)


def notify_error(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
    """Add error notification to current collection"""
    return get_notifications().error(message, type, **kwargs)


def notify_validation_error(message: str, field_name: Optional[str] = None, 
                          value: Optional[Any] = None, entity_id: Optional[str] = None, **kwargs) -> NotificationDetail:
    """Add validation error with field details"""
    return get_notifications().validation_error(message, field_name=field_name, value=value, entity_id=entity_id, **kwargs)


def notify_database_error(message: str, **kwargs) -> NotificationDetail:
    """Add database error"""
    return get_notifications().database_error(message, **kwargs)