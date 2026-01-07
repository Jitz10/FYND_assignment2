import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from .database import _normalize, get_database


_connections: set[WebSocket] = set()
_lock = asyncio.Lock()
logger = logging.getLogger(__name__)

_CLASSIFICATION_KEYS = ["product_issue", "delivery_issue", "sarcasm", "genuine", "other"]


def _build_match(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    match: Dict[str, Any] = {}
    if filters:
        match.update({k: v for k, v in filters.items() if v})
    return match


async def compute_analytics_summary(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return aggregate analytics snapshot for reviews with optional filters."""
    db = get_database()
    coll = db["reviews"]
    query = _build_match(filters)

    total_reviews = await coll.count_documents(query)

    avg_rating = 0.0
    avg_doc = await coll.aggregate([
        {"$match": query},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]).to_list(1)
    if avg_doc:
        avg_rating = round(float(avg_doc[0].get("avg", 0.0)), 2)

    classification_counts: Dict[str, int] = {k: 0 for k in _CLASSIFICATION_KEYS}
    class_docs = await coll.aggregate([
        {"$match": query},
        {"$group": {"_id": "$classification", "count": {"$sum": 1}}},
    ]).to_list(None)
    for item in class_docs:
        key = item.get("_id") or "other"
        if key not in classification_counts:
            classification_counts[key] = 0
        classification_counts[key] = int(item.get("count", 0))

    website_breakdown = await coll.aggregate([
        {"$match": query},
        {
            "$group": {
                "_id": "$website",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$rating"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "website": "$_id",
                "count": 1,
                "avg_rating": {"$round": ["$avg_rating", 2]},
            }
        },
        {"$sort": {"count": -1}},
    ]).to_list(None)

    product_breakdown = await coll.aggregate([
        {"$match": query},
        {
            "$group": {
                "_id": "$product",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$rating"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "product": "$_id",
                "count": 1,
                "avg_rating": {"$round": ["$avg_rating", 2]},
            }
        },
        {"$sort": {"count": -1}},
    ]).to_list(None)

    latest_reviews: List[Dict[str, Any]] = []
    cursor = coll.find(query).sort("created_at", -1).limit(5)
    async for doc in cursor:
        latest_reviews.append(_normalize(doc))

    return {
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "classification_counts": classification_counts,
        "website_breakdown": website_breakdown,
        "product_breakdown": product_breakdown,
        "latest_reviews": latest_reviews,
    }


async def register_analytics_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    async with _lock:
        _connections.add(websocket)
    await _send_snapshot(websocket)


async def unregister_analytics_ws(websocket: WebSocket) -> None:
    async with _lock:
        _connections.discard(websocket)


async def broadcast_analytics_update() -> None:
    try:
        summary = await compute_analytics_summary()
    except Exception as exc:
        logger.warning("Analytics broadcast skipped: %s", exc)
        return
    async with _lock:
        targets = list(_connections)
    dead: List[WebSocket] = []
    for ws in targets:
        try:
            await ws.send_json({"type": "analytics_snapshot", "summary": summary})
        except Exception:
            dead.append(ws)
    if dead:
        async with _lock:
            for ws in dead:
                _connections.discard(ws)


async def _send_snapshot(websocket: WebSocket) -> None:
    try:
        summary = await compute_analytics_summary()
        await websocket.send_json({"type": "analytics_snapshot", "summary": summary})
    except Exception as exc:
        logger.warning("Snapshot send failed: %s", exc)
        await unregister_analytics_ws(websocket)
