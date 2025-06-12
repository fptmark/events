from fastapi import APIRouter
from typing import List
import logging
from app.models.event_model import Event, EventCreate, EventUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[Event])
async def list_events() -> dict:
    """List all events"""
    try:
        logger.info("Fetching all events")
        events, validation_errors = await Event.find_all()
        records = len(events)
        logger.info(f"Retrieved {records} events")
        return list(events)

        response = {
            "data": list(event),
            "validation_errors": [
                {
                    "message": ve.message,
                    "entity": ve.entity,
                    "invalid_fields": [f.to_dict() for f in ve.invalid_fields]
                }
                for ve in validation_errors
            ] if validation_errors else []
        }
        return response
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise


@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str) -> Event:
    """Get a specific event by ID"""
    try:
        logger.info(f"Fetching event with ID: {event_id }")
        event = await Event.get(event_id)
        logger.info(f"Retrieved event: {event.id }")
        return event
    except NotFoundError:
        logger.warning(f"Event not found: {event_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting event {event_id }: {e}")
        raise


@router.post("", response_model=Event)
async def create_event(event_data: EventCreate) -> Event:
    """Create a new event"""
    try:
        logger.info(f"Creating event with data: {event_data }")
        event = Event(**event_data.model_dump())
        result = await event.save()
        logger.info(f"Event created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating event: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise


@router.put("/{event_id}", response_model=Event)
async def update_event(event_id: str, event_data: EventUpdate) -> Event:
    """Update an existing event"""
    try:
        logger.info(f"Updating event {event_id } with data: {event_data }")

        existing = await Event.get(event_id)
        logger.info(f"Found existing event: {existing.id}")

        event = Event(**event_data.model_dump())
        result = await event.save(event_id)
        logger.info(f"Event updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating event {event_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}")
        raise


@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """Delete a event"""
    try:
        logger.info(f"Deleting event: {event_id}")
        event = await Event.get(event_id)
        await event.delete()
        logger.info(f"Event deleted successfully: {event_id}")
        return {"message": "Event deleted successfully"}
    except NotFoundError:
        logger.warning(f"Event not found for deletion: {event_id}")
        raise