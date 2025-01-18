from pymongo import MongoClient

# MongoDB connection string
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)

# Database reference
db = client["event_management"]
