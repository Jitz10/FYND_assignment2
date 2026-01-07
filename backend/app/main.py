from datetime import datetime
from pathlib import Path
import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .services.ai import generate_summary_and_suggestions
from .services.analytics import (
    broadcast_analytics_update,
    compute_analytics_summary,
    register_analytics_ws,
    unregister_analytics_ws,
)
from .services.insights import generate_insights
from .services.database import get_all_reviews, save_review, ping_database


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    feedback: str = Field(min_length=1, max_length=4000, description="User feedback text")
    website: str = Field(min_length=1, description="Website identifier")
    product: str = Field(min_length=1, description="Product identifier")


class ReviewRecord(BaseModel):
    id: str = Field(alias="_id")
    rating: int
    feedback: str
    website: str = ""
    product: str = ""
    ai_summary_user: str = ""
    ai_suggestions_user: List[str] = Field(default_factory=list)
    ai_summary_vendor: str = ""
    ai_suggestions_vendor: List[str] = Field(default_factory=list)
    classification: str = ""
    created_at: Optional[str] = None

    class Config:
        populate_by_name = True


app = FastAPI(title="Review AI Service", version="0.2.0")

# Allow browser clients (frontend served locally or via file://) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables from .env in the backend directory (one level up from this file)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@app.get("/")
async def root():
    return {"status": "ok", "message": "Review AI Service"}


# Serve frontend dashboard at /ui
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "user dashboard"
app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")

# Serve admin analytics dashboard at /analytics-ui
FRONTEND_ANALYTICS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "analytics"
app.mount("/analytics-ui", StaticFiles(directory=FRONTEND_ANALYTICS_DIR, html=True), name="analytics-ui")


@app.post("/reviews", response_model=ReviewRecord)
async def create_review(review: ReviewIn) -> ReviewRecord:
    (
        user_summary,
        user_suggestions,
        vendor_summary,
        vendor_suggestions,
        classification,
    ) = await generate_summary_and_suggestions(
        review.rating, review.feedback, review.website, review.product
    )
    created_at = datetime.utcnow()
    doc = {
        "rating": review.rating,
        "feedback": review.feedback,
        "website": review.website,
        "product": review.product,
        "ai_summary_user": user_summary,
        "ai_suggestions_user": user_suggestions,
        "ai_summary_vendor": vendor_summary,
        "ai_suggestions_vendor": vendor_suggestions,
        "classification": classification,
        "created_at": created_at,
    }
    try:
        inserted_id = await save_review(doc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please check MONGODB_URI/connectivity.",
        ) from exc

    # Push analytics update without blocking the response
    asyncio.create_task(broadcast_analytics_update())

    return ReviewRecord(
        _id=inserted_id,
        rating=review.rating,
        feedback=review.feedback,
        website=review.website,
        product=review.product,
        ai_summary_user=user_summary,
        ai_suggestions_user=user_suggestions,
        ai_summary_vendor=vendor_summary,
        ai_suggestions_vendor=vendor_suggestions,
        classification=classification,
        created_at=created_at.isoformat() + "Z",
    )


@app.get("/reviews", response_model=List[ReviewRecord])
async def list_reviews() -> List[ReviewRecord]:
    try:
        records = await get_all_reviews()
        return records
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please check MONGODB_URI/connectivity.",
        ) from exc


@app.get("/health")
async def health():
    db_ok = await ping_database()
    return {"status": "ok", "db": "up" if db_ok else "down"}


@app.get("/analytics/summary")
async def analytics_summary(
    website: Optional[str] = None,
    product: Optional[str] = None,
    classification: Optional[str] = None,
):
    filters = {}
    if website:
        filters["website"] = website
    if product:
        filters["product"] = product
    if classification:
        filters["classification"] = classification
    try:
        summary = await compute_analytics_summary(filters)
        return summary
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please check MONGODB_URI/connectivity.",
        ) from exc


@app.get("/analytics/insights")
async def analytics_insights(
    website: Optional[str] = None,
    product: Optional[str] = None,
    classification: Optional[str] = None,
):
    filters = {}
    if website:
        filters["website"] = website
    if product:
        filters["product"] = product
    if classification:
        filters["classification"] = classification
    try:
        insights = await generate_insights(filters)
        return insights
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics insights unavailable. Please check MONGODB_URI/connectivity.",
        ) from exc


@app.websocket("/ws/analytics")
async def analytics_ws(websocket: WebSocket):
    await register_analytics_ws(websocket)
    try:
        while True:
            # Keep the connection alive; payloads are pushed from server on changes
            await websocket.receive_text()
    except WebSocketDisconnect:
        await unregister_analytics_ws(websocket)
