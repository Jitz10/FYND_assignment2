from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List

from .services.ai import generate_summary_and_suggestions


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    feedback: str = Field(min_length=1, max_length=4000, description="User feedback text")


class ReviewOut(BaseModel):
    rating: int
    feedback: str
    ai_summary: str
    ai_suggestions: List[str]


app = FastAPI(title="Review AI Service", version="0.1.0")


@app.post("/reviews", response_model=ReviewOut)
async def create_review(review: ReviewIn) -> ReviewOut:
    summary, suggestions = await generate_summary_and_suggestions(
        review.rating, review.feedback
    )
    return ReviewOut(
        rating=review.rating,
        feedback=review.feedback,
        ai_summary=summary,
        ai_suggestions=suggestions,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
