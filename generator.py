import os
from zipfile import ZipFile

# Base project directory
base_dir = "events"

# Directories to create
directories = [
    f"{base_dir}/models",
    f"{base_dir}/routes",
    f"{base_dir}/utils"
]

# Base files
base_files = {
    "main.py": """\
from fastapi import FastAPI
from routes import (
    account_routes, user_routes, profile_routes, tag_affinity_routes,
    event_routes, user_event_routes, url_routes, crawl_routes
)

app = FastAPI()

# Include routers
app.include_router(account_routes.router, prefix="/accounts", tags=["Accounts"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(profile_routes.router, prefix="/profiles", tags=["Profiles"])
app.include_router(tag_affinity_routes.router, prefix="/tag-affinities", tags=["Tag Affinities"])
app.include_router(event_routes.router, prefix="/events", tags=["Events"])
app.include_router(user_event_routes.router, prefix="/user-events", tags=["User Events"])
app.include_router(url_routes.router, prefix="/urls", tags=["URLs"])
app.include_router(crawl_routes.router, prefix="/crawls", tags=["Crawls"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Event Management System"}
""",
    "db.py": """\
from pymongo import MongoClient

# MongoDB connection string
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)

# Database reference
db = client["event_management"]
""",
    "config.py": """\
class Config:
    PROJECT_NAME = "Event Management System"
    VERSION = "1.0.0"
    MONGO_URI = "mongodb://localhost:27017"
""",
    "requirements.txt": """\
fastapi
uvicorn
pymongo
""",
    "README.md": """\
# Event Management System

This is a FastAPI-based application for managing events, users, profiles, and more.
"""
}

# Models
models = {
    "account_models.py": """\
from pydantic import BaseModel, Field
from datetime import datetime

class Account(BaseModel):
    id: str = Field(..., alias="_id")
    expiredAt: datetime
    createdAt: datetime
""",
    "user_models.py": """\
from pydantic import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    id: str = Field(..., alias="_id")
    accountId: str
    username: str
    password: str
    isOwner: bool
    createdAt: datetime
""",
    "profile_models.py": """\
from pydantic import BaseModel, Field

class Profile(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    name: str
    preferences: dict
    radius: int
""",
    "tag_affinity_models.py": """\
from pydantic import BaseModel, Field

class TagAffinity(BaseModel):
    id: str = Field(..., alias="_id")
    profileId: str
    tag: str
    affinity: int  # Positive = Like, Negative = Dislike
""",
    "event_models.py": """\
from pydantic import BaseModel, Field
from datetime import datetime

class Event(BaseModel):
    id: str = Field(..., alias="_id")
    title: str
    dateTime: datetime
    location: str
    cost: float
    numOfExpectedAttendees: int
    recurrence: str
    tags: list[str]
""",
    "user_event_models.py": """\
from pydantic import BaseModel, Field

class UserEvent(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    eventId: str
    attended: bool
    rating: int
    note: str
""",
    "url_models.py": """\
from pydantic import BaseModel, Field

class URL(BaseModel):
    id: str = Field(..., alias="_id")
    url: str
    params: dict
""",
    "crawl_models.py": """\
from pydantic import BaseModel, Field
from datetime import datetime

class Crawl(BaseModel):
    id: str = Field(..., alias="_id")
    urlId: str
    lastParsedDate: datetime
    parseStatus: dict
    errorsEncountered: list[str]
""",
}

# CRUD Routes (same for all entities)
route_template = """\
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
"""

routes = {
    "account_routes.py": route_template,
    "user_routes.py": route_template,
    "profile_routes.py": route_template,
    "tag_affinity_routes.py": route_template,
    "event_routes.py": route_template,
    "user_event_routes.py": route_template,
    "url_routes.py": route_template,
    "crawl_routes.py": route_template,
}

# Utilities
utils = {
    "helpers.py": """\
def format_response(data):
    return {"status": "success", "data": data}
"""
}

# Create directories
def create_directories():
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Write files
def write_files(file_dict, folder):
    for filename, content in file_dict.items():
        with open(f"{folder}/{filename}", "w") as file:
            file.write(content)

# Generate project
def generate_project():
    create_directories()
    write_files(base_files, base_dir)
    write_files(models, f"{base_dir}/models")
    write_files(routes, f"{base_dir}/routes")
    write_files(utils, f"{base_dir}/utils")

    # Zip the project
    zip_file = f"{base_dir}.zip"
    with ZipFile(zip_file, "w") as zipf:
        for root, _, files in os.walk(base_dir):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, arcname=os.path.relpath(full_path, base_dir))
    print(f"Project zipped at {zip_file}")

generate_project()
