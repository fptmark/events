from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
import logging
from contextvars import ContextVar


def _default_timestamp() -> datetime:
    """Default timestamp factory"""
    return datetime.now(timezone.utc)


class NotificationType(Enum):
    """Types of notifications - determines whether it's an error or warning"""
    # System-level errors (go in errors array)
    DATABASE = "database"
    SYSTEM = "system" 
    SECURITY = "security"
    APPLICATION = "application"
    
    # Entity-level warnings (go in warnings grouped by entity/id)
    VALIDATION = "validation"
    BUSINESS = "business"


@dataclass
class NotificationDetail:
    """Single notification detail"""
    message: str
    type: NotificationType
    entity: Optional[str] = None
    entity_id: Optional[str] = None
    field_name: Optional[str] = None
    details: List[str] = dataclass_field(default_factory=list)  # Flat string array

    def add_detail(self, detail_message: str) -> None:
        """Add a detail message to this notification"""
        self.details.append(detail_message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for new API response format"""
        result = {
            "type": self.type.value,
            "message": self.message,
            "details": self.details
        }
        
        # Include field if provided (for validation/business warnings)
        if self.field_name:
            result["field"] = self.field_name
            
        return result


class SimpleNotificationCollection:
    """Simplified notification collection for REST operations"""
    
    def __init__(self, entity: Optional[str] = None, operation: Optional[str] = None):
        self.entity = entity
        self.operation = operation
        self.notifications: List[NotificationDetail] = []
        
    def add(self, message: str, type: NotificationType, 
            entity: Optional[str] = None, field_name: Optional[str] = None,
            entity_id: Optional[str] = None) -> NotificationDetail:
        """Add a notification and return it for potential detail addition"""
        notification = NotificationDetail(
            message=message,
            type=type,
            entity=entity or self.entity,
            entity_id=entity_id,
            field_name=field_name
        )
        self.notifications.append(notification)
        
        # Log to console with details
        self._log_notification(notification)
        
        return notification

    def add_error(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
        """Add system error (database, system, security)"""
        return self.add(message, type, **kwargs)

    def add_warning(self, message: str, type: NotificationType = NotificationType.BUSINESS, **kwargs) -> NotificationDetail:
        """Add entity warning (business, validation)"""
        return self.add(message, type, **kwargs)

    def validation_error(self, message: str, field_name: Optional[str] = None, 
                        entity_id: Optional[str] = None, **kwargs) -> NotificationDetail:
        """Add validation warning with field details"""
        return self.add(message, NotificationType.VALIDATION, 
                       field_name=field_name, entity_id=entity_id, **kwargs)

    def business_error(self, message: str, field_name: Optional[str] = None,
                      entity_id: Optional[str] = None, **kwargs) -> NotificationDetail:
        """Add business logic warning"""
        return self.add(message, NotificationType.BUSINESS,
                       field_name=field_name, entity_id=entity_id, **kwargs)

    def database_error(self, message: str, **kwargs) -> NotificationDetail:
        """Add database error"""
        return self.add(message, NotificationType.DATABASE, **kwargs)

    def system_error(self, message: str, **kwargs) -> NotificationDetail:
        """Add system error"""
        return self.add(message, NotificationType.SYSTEM, **kwargs)

    def application_error(self, message: str, **kwargs) -> NotificationDetail:
        """Add application error (user-caused errors like invalid field names)"""
        return self.add(message, NotificationType.APPLICATION, **kwargs)

    def security_error(self, message: str, **kwargs) -> NotificationDetail:
        """Add security error"""
        return self.add(message, NotificationType.SECURITY, **kwargs)

    def has_errors(self) -> bool:
        """Check if collection contains any system errors (database, system, security, application)"""
        return any(n.type in [NotificationType.DATABASE, NotificationType.SYSTEM, NotificationType.SECURITY, NotificationType.APPLICATION] 
                  for n in self.notifications)

    def has_warnings(self) -> bool:
        """Check if collection contains any entity warnings (business, validation)"""
        return any(n.type in [NotificationType.BUSINESS, NotificationType.VALIDATION] 
                  for n in self.notifications)

    def to_response(self, data: Any = None) -> Dict[str, Any]:
        """Convert to new API response format with errors/warnings structure"""
        # Separate notifications by type
        errors = []
        warnings: Dict[str, Any] = {}
        
        for notification in self.notifications:
            if notification.type in [NotificationType.DATABASE, NotificationType.SYSTEM, NotificationType.SECURITY, NotificationType.APPLICATION]:
                # System errors go in errors array
                errors.append(notification.to_dict())
            else:
                # Business/validation warnings go in warnings grouped by entity/id
                entity_type = notification.entity or "unknown"
                entity_id = notification.entity_id or "unknown"
                
                if entity_type not in warnings:
                    warnings[entity_type] = {}
                if entity_id not in warnings[entity_type]:
                    warnings[entity_type][entity_id] = []
                    
                warnings[entity_type][entity_id].append(notification.to_dict())
        
        # Determine status
        if errors:
            status = "failed"
        elif warnings:
            status = "warning" 
        else:
            status = "success"
        
        # Build response
        response = {
            "status": status,
            "data": data
        }
        
        # Add notifications only if there are any
        if errors or warnings:
            notifications = {}
            if errors:
                notifications["errors"] = errors
            if warnings:
                notifications["warnings"] = warnings
            response["notifications"] = notifications
        
        return response

    def to_entity_grouped_response(self, data: Any = None, is_bulk: bool = False) -> Dict[str, Any]:
        """Legacy method - use to_response instead"""
        return self.to_response(data)

    def _log_notification(self, notification: NotificationDetail, indent: int = 0) -> None:
        """Log notification and its details to console"""
        # Determine log level based on type
        if notification.type in [NotificationType.DATABASE, NotificationType.SYSTEM, NotificationType.SECURITY, NotificationType.APPLICATION]:
            log_level = logging.ERROR
            level_name = "ERROR"
        else:
            log_level = logging.WARNING
            level_name = "WARNING"
        
        prefix = "  " * indent
        
        # Entity part with ID
        if notification.entity and notification.entity_id:
            entity_part = f"{notification.entity}:{notification.entity_id}"
        elif notification.entity:
            entity_part = notification.entity
        else:
            entity_part = "System"
        
        # Field part
        field_part = ""
        if notification.field_name:
            field_part = f"{notification.field_name} "
        
        # Build final log message
        log_msg = f"{prefix}[{level_name}] {entity_part} [{notification.type.value}] {field_part}{notification.message}"
        
        logging.log(log_level, log_msg)
        
        # Log details with increased indentation
        for detail in notification.details:
            detail_msg = f"{prefix}  - {detail}"
            logging.log(log_level, detail_msg)

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
def notify_error(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> NotificationDetail:
    """Add system error (database, system, security)"""
    return get_notifications().add_error(message, type, **kwargs)


def notify_warning(message: str, type: NotificationType = NotificationType.BUSINESS, **kwargs) -> NotificationDetail:
    """Add entity warning (business, validation)"""
    return get_notifications().add_warning(message, type, **kwargs)


def notify_validation_error(message: str, field_name: Optional[str] = None, 
                          entity_id: Optional[str] = None, **kwargs) -> NotificationDetail:
    """Add validation warning with field details"""
    return get_notifications().validation_error(message, field_name=field_name, entity_id=entity_id, **kwargs)


def notify_business_error(message: str, field_name: Optional[str] = None, 
                         entity_id: Optional[str] = None, **kwargs) -> NotificationDetail:
    """Add business logic warning"""
    return get_notifications().business_error(message, field_name=field_name, entity_id=entity_id, **kwargs)


def notify_database_error(message: str, **kwargs) -> NotificationDetail:
    """Add database error"""
    return get_notifications().database_error(message, **kwargs)


def notify_system_error(message: str, **kwargs) -> NotificationDetail:
    """Add system error"""
    return get_notifications().system_error(message, **kwargs)


def notify_application_error(message: str, **kwargs) -> NotificationDetail:
    """Add application error (user-caused errors like invalid field names)"""
    return get_notifications().application_error(message, **kwargs)


def notify_security_error(message: str, **kwargs) -> NotificationDetail:
    """Add security error"""
    return get_notifications().security_error(message, **kwargs)