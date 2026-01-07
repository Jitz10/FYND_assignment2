from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .services.ai import generate_summary_and_suggestions
from .services.database import get_all_reviews, save_review, ping_database


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    feedback: str = Field(min_length=1, max_length=4000, description="User feedback text")


class ReviewRecord(BaseModel):
    id: str = Field(alias="_id")
    rating: int
    feedback: str
    ai_summary: str
    ai_suggestions: List[str]
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


@app.post("/reviews", response_model=ReviewRecord)
async def create_review(review: ReviewIn) -> ReviewRecord:
    summary, suggestions = await generate_summary_and_suggestions(review.rating, review.feedback)
    created_at = datetime.utcnow()
    doc = {
        "rating": review.rating,
        "feedback": review.feedback,
        "ai_summary": summary,
        "ai_suggestions": suggestions,
        "created_at": created_at,
    }
    try:
        inserted_id = await save_review(doc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please check MONGODB_URI/connectivity.",
        ) from exc

    return ReviewRecord(
        _id=inserted_id,
        rating=review.rating,
        feedback=review.feedback,
        ai_summary=summary,
        ai_suggestions=suggestions,
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
