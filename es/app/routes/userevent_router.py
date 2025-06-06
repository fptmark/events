from fastapi import APIRouter
from typing import List
from app.models.userevent_model import UserEvent
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("/", response_model=List[UserEvent])
async def list_userevents() -> List[UserEvent]:
    """List all user events"""
    userevents = await UserEvent.find_all()
    return list(userevents)  # Convert Sequence to List

@router.get("/{userevent_id}", response_model=UserEvent)
async def get_userevent(userevent_id: str) -> UserEvent:
    """Get a specific user event by ID"""
    return await UserEvent.get(userevent_id)

@router.post("/", response_model=UserEvent)
async def create_userevent(userevent: UserEvent) -> UserEvent:
    """Create a new user event"""
    # Validation is handled by Pydantic model
    return await userevent.save()

@router.put("/{userevent_id}", response_model=UserEvent)
async def update_userevent(userevent_id: str, userevent: UserEvent) -> UserEvent:
    """Update an existing user event"""
    # Check if user event exists
    existing = await UserEvent.get(userevent_id)
    
    # Update fields
    userevent.id = userevent_id
    userevent.createdAt = existing.createdAt
    
    # Save changes
    return await userevent.save()

@router.delete("/{userevent_id}")
async def delete_userevent(userevent_id: str):
    """Delete a user event"""
    userevent = await UserEvent.get(userevent_id)
    if not userevent:
        raise NotFoundError("UserEvent", userevent_id)
    await userevent.delete()
    return {"message": "User event deleted successfully"}

@router.get('/metadata')
async def get_userevent_metadata():
    """Get metadata for UserEvent entity."""
    return UserEvent.get_metadata() 