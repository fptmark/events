from bson.objectid import ObjectId
from typing import Dict, Any

def serialize_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize MongoDB document for JSON response.
    Convert ObjectId to string.
    """
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc
