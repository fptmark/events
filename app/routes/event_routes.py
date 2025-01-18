from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_all():
    return {{"message": "Get all"}}

@router.post("/")
def create():
    return {{"message": "Create"}}

@router.get("/{item_id}")
def get_one(item_id: str):
    return {{"message": f"Get one with ID {item_id}"}}

@router.put("/{item_id}")
def update(item_id: str):
    return {{"message": f"Update with ID {item_id}"}}

@router.delete("/{item_id}")
def delete(item_id: str):
    return {{"message": f"Delete with ID {item_id}"}}
