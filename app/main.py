# import sys
# print(f"Python PATH: {sys.path}")

from fastapi import FastAPI
from app.routes import (
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
