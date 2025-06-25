from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
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
    timestamp: datetime = field(default_factory=_default_timestamp)
    details: List['NotificationDetail'] = field(default_factory=list)

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
            value=kwargs.get('value')
        )
        self.details.append(detail)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
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


class SimpleNotificationCollection:
    """Simplified notification collection for REST operations"""
    
    def __init__(self, entity: Optional[str] = None, operation: Optional[str] = None):
        self.entity = entity
        self.operation = operation
        self.notifications: List[NotificationDetail] = []
        
    def add(self, message: str, level: NotificationLevel, type: NotificationType, 
            entity: Optional[str] = None, operation: Optional[str] = None,
            field_name: Optional[str] = None, value: Optional[Any] = None) -> NotificationDetail:
        """Add a notification and return it for potential detail addition"""
        notification = NotificationDetail(
            message=message,
            level=level,
            type=type,
            entity=entity or self.entity,
            operation=operation or self.operation,
            field_name=field_name,
            value=value
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

    def validation_error(self, message: str, field: Optional[str] = None, 
                        value: Optional[Any] = None, **kwargs) -> NotificationDetail:
        """Add validation error with field details"""
        return self.error(message, NotificationType.VALIDATION, 
                         field_name=field, value=value, **kwargs)

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

    def to_response(self, data: Any = None) -> Dict[str, Any]:
        """Convert to standard API response format"""
        message, level = self.get_primary_message()
        
        response = {
            "data": data,
            "message": message,
            "level": level
        }
        
        # Include notifications if there are multiple or if there are details
        if len(self.notifications) > 1 or any(n.details for n in self.notifications):
            response["notifications"] = [n.to_dict() for n in self.notifications]
            response["summary"] = self.get_summary()
        
        return response

    def _log_notification(self, notification: NotificationDetail, indent: int = 0) -> None:
        """Log notification and its details to console"""
        log_level_map = {
            NotificationLevel.SUCCESS: logging.INFO,
            NotificationLevel.INFO: logging.INFO,
            NotificationLevel.WARNING: logging.WARNING,
            NotificationLevel.ERROR: logging.ERROR
        }
        
        prefix = "  " * indent
        log_msg = f"{prefix}[{notification.type.value}] {notification.message}"
        
        if notification.entity and indent == 0:
            log_msg = f"{notification.entity}: {log_msg}"
        if notification.operation and indent == 0:
            log_msg = f"{log_msg} ({notification.operation})"
        if notification.field_name:
            log_msg = f"{log_msg} [field: {notification.field_name}]"
            
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


def notify_validation_error(message: str, field: Optional[str] = None, 
                          value: Optional[Any] = None, **kwargs) -> NotificationDetail:
    """Add validation error with field details"""
    return get_notifications().validation_error(message, field=field, value=value, **kwargs)


def notify_database_error(message: str, **kwargs) -> NotificationDetail:
    """Add database error"""
    return get_notifications().database_error(message, **kwargs)