# FastAPI Event Service

This project manages users, events, and related data using FastAPI and MongoDB.

## Collections
1. **Users**: User profiles and preferences.
2. **Events**: Event information (e.g., title, date, tags).
3. **User Events**: Links users to events with feedback.
4. **User Tag Affinities**: Tracks user preferences for tags.
5. **URLs**: Tracks sources for crawling.
6. **Crawls**: Logs crawl attempts and their results.

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Start the app: `uvicorn app.main:app --reload`
3. Access the API docs: `http://127.0.0.1:8000/docs`
