import os
from datetime import datetime
from typing import Dict, List

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
print("Using MongoDB URI:", MONGODB_URI)
DB_NAME = "review_system"
COLLECTION_NAME = "reviews"

_client: AsyncIOMotorClient | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return _get_client()[DB_NAME]


async def ping_database() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        client = _get_client()
        await client.admin.command("ping")
        return True
    except Exception:
        return False


def _normalize(doc: Dict) -> Dict:
    cleaned = dict(doc)
    if "_id" in cleaned and isinstance(cleaned["_id"], ObjectId):
        cleaned["_id"] = str(cleaned["_id"])
    created_at = cleaned.get("created_at")
    if isinstance(created_at, datetime):
        cleaned["created_at"] = created_at.isoformat() + "Z"
    return cleaned


async def save_review(review: Dict) -> str:
    db = get_database()
    payload = dict(review)
    payload.setdefault("created_at", datetime.utcnow())
    result = await db[COLLECTION_NAME].insert_one(payload)
    return str(result.inserted_id)


async def get_all_reviews() -> List[Dict]:
    db = get_database()
    cursor = db[COLLECTION_NAME].find().sort("created_at", -1)
    docs: List[Dict] = []
    async for doc in cursor:
        docs.append(_normalize(doc))
    return docs