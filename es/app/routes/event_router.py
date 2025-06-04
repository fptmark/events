from fastapi import APIRouter
from typing import List, Optional
from datetime import datetime
from ..models.event_model import Event, EventCreate, EventUpdate
from ..errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("", response_model=List[Event])
async def list_events(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> List[Event]:
    """List all events with optional date filtering"""
    events = await Event.find_all()
    filtered_events = list(events)  # Convert Sequence to List
    
    if from_date:
        filtered_events = [e for e in filtered_events if e.dateTime >= from_date]
    if to_date:
        filtered_events = [e for e in filtered_events if e.dateTime <= to_date]
        
    return filtered_events

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str) -> Event:
    """Get a specific event by ID"""
    event = await Event.get(event_id)
    if not event:
        raise NotFoundError("Event", event_id)
    return event

@router.post("", response_model=Event)
async def create_event(event_data: EventCreate) -> Event:
    """Create a new event"""
    event = Event(**event_data.model_dump())
    return await event.save()

@router.put("/{event_id}", response_model=Event)
async def update_event(event_id: str, event_data: EventUpdate) -> Event:
    """Update an existing event"""
    # Check if event exists
    existing = await Event.get(event_id)
    if not existing:
        raise NotFoundError("Event", event_id)
    
    # Update fields
    event = Event(**event_data.model_dump())
    event.id = event_id
    event.createdAt = existing.createdAt
    
    # Save changes
    return await event.save()

@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """Delete an event"""
    event = await Event.get(event_id)
    if not event:
        raise NotFoundError("Event", event_id)
    await event.delete()
    return {"message": "Event deleted successfully"}

@router.get("/metadata")
async def get_event_metadata():
    """Get metadata for Event entity."""
    return Event.get_metadata()