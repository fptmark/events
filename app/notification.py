from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
from contextvars import ContextVar


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
class Notification:
    """Single notification message"""
    message: str
    level: NotificationLevel
    type: NotificationType
    entity: Optional[str] = None
    operation: Optional[str] = None
    field: Optional[str] = None
    value: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "message": self.message,
            "level": self.level.value,
            "type": self.type.value,
            "entity": self.entity,
            "operation": self.operation,
            "field": self.field,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


@dataclass
class NotificationCollection:
    """Collection of notifications for a request/operation"""
    notifications: List[Notification] = field(default_factory=list)
    operation_id: Optional[str] = None
    entity: Optional[str] = None

    def add(self, message: str, level: NotificationLevel, type: NotificationType, 
            entity: Optional[str] = None, operation: Optional[str] = None,
            field: Optional[str] = None, value: Optional[Any] = None,
            context: Optional[Dict[str, Any]] = None) -> None:
        """Add a notification to the collection"""
        notification = Notification(
            message=message,
            level=level,
            type=type,
            entity=entity or self.entity,
            operation=operation,
            field=field,
            value=value,
            context=context or {}
        )
        self.notifications.append(notification)
        
        # Also log to console for development
        log_level = {
            NotificationLevel.SUCCESS: logging.INFO,
            NotificationLevel.INFO: logging.INFO,
            NotificationLevel.WARNING: logging.WARNING,
            NotificationLevel.ERROR: logging.ERROR
        }
        
        log_msg = f"[{type.value}] {message}"
        if entity:
            log_msg = f"{entity}: {log_msg}"
        if operation:
            log_msg = f"{log_msg} ({operation})"
            
        logging.log(log_level[level], log_msg)

    def success(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add success notification"""
        self.add(message, NotificationLevel.SUCCESS, type, **kwargs)

    def info(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add info notification"""
        self.add(message, NotificationLevel.INFO, type, **kwargs)

    def warning(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add warning notification"""
        self.add(message, NotificationLevel.WARNING, type, **kwargs)

    def error(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add error notification"""
        self.add(message, NotificationLevel.ERROR, type, **kwargs)

    def has_errors(self) -> bool:
        """Check if collection contains any errors"""
        return any(n.level == NotificationLevel.ERROR for n in self.notifications)

    def has_warnings(self) -> bool:
        """Check if collection contains any warnings"""
        return any(n.level == NotificationLevel.WARNING for n in self.notifications)

    def get_by_level(self, level: NotificationLevel) -> List[Notification]:
        """Get notifications by level"""
        return [n for n in self.notifications if n.level == level]

    def get_by_type(self, type: NotificationType) -> List[Notification]:
        """Get notifications by type"""
        return [n for n in self.notifications if n.type == type]

    def clear(self) -> None:
        """Clear all notifications"""
        self.notifications.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "notifications": [n.to_dict() for n in self.notifications],
            "operation_id": self.operation_id,
            "entity": self.entity,
            "summary": {
                "total": len(self.notifications),
                "errors": len(self.get_by_level(NotificationLevel.ERROR)),
                "warnings": len(self.get_by_level(NotificationLevel.WARNING)),
                "success": len(self.get_by_level(NotificationLevel.SUCCESS)),
                "info": len(self.get_by_level(NotificationLevel.INFO))
            }
        }


class NotificationManager:
    """
    Singleton notification manager with context-aware notification collection.
    Uses contextvars to maintain separate notification collections per async context.
    """
    
    _instance: Optional['NotificationManager'] = None
    _current_collection: ContextVar[Optional[NotificationCollection]] = ContextVar('current_collection', default=None)

    def __new__(cls) -> 'NotificationManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'NotificationManager':
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_operation(self, operation_id: Optional[str] = None, entity: Optional[str] = None) -> NotificationCollection:
        """Start a new operation context and return the collection"""
        collection = NotificationCollection(operation_id=operation_id, entity=entity)
        self._current_collection.set(collection)
        return collection

    def get_current(self) -> NotificationCollection:
        """Get the current notification collection"""
        collection = self._current_collection.get()
        if collection is None:
            # Auto-create a collection if none exists
            collection = self.start_operation()
        return collection

    def end_operation(self) -> NotificationCollection:
        """End the current operation and return the collection"""
        collection = self.get_current()
        self._current_collection.set(None)
        return collection

    # Convenience methods that delegate to current collection
    def add(self, message: str, level: NotificationLevel, type: NotificationType, **kwargs) -> None:
        """Add notification to current collection"""
        self.get_current().add(message, level, type, **kwargs)

    def success(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add success notification to current collection"""
        self.get_current().success(message, type, **kwargs)

    def info(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add info notification to current collection"""
        self.get_current().info(message, type, **kwargs)

    def warning(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add warning notification to current collection"""
        self.get_current().warning(message, type, **kwargs)

    def error(self, message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
        """Add error notification to current collection"""
        self.get_current().error(message, type, **kwargs)

    def has_errors(self) -> bool:
        """Check if current collection has errors"""
        return self.get_current().has_errors()

    def has_warnings(self) -> bool:
        """Check if current collection has warnings"""
        return self.get_current().has_warnings()

    def clear(self) -> None:
        """Clear current collection"""
        self.get_current().clear()


# Global convenience functions
def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance"""
    return NotificationManager.get_instance()


def notify_success(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
    """Global convenience function for success notifications"""
    get_notification_manager().success(message, type, **kwargs)


def notify_info(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
    """Global convenience function for info notifications"""
    get_notification_manager().info(message, type, **kwargs)


def notify_warning(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
    """Global convenience function for warning notifications"""
    get_notification_manager().warning(message, type, **kwargs)


def notify_error(message: str, type: NotificationType = NotificationType.SYSTEM, **kwargs) -> None:
    """Global convenience function for error notifications"""
    get_notification_manager().error(message, type, **kwargs)


def notify_validation_error(message: str, entity: str, field: Optional[str] = None, 
                          value: Optional[Any] = None, **kwargs) -> None:
    """Convenience function for validation errors"""
    get_notification_manager().error(
        message, 
        NotificationType.VALIDATION, 
        entity=entity, 
        field=field, 
        value=value, 
        **kwargs
    )


def notify_database_warning(message: str, entity: str, operation: Optional[str] = None, **kwargs) -> None:
    """Convenience function for database warnings"""
    get_notification_manager().warning(
        message, 
        NotificationType.DATABASE, 
        entity=entity, 
        operation=operation, 
        **kwargs
    )