import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load backend .env so the same MONGODB_URI is used as the app
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "review_system"
COLLECTION_NAME = "reviews"


def base_doc(website: str, product: str, rating: int, feedback: str, classification: str):
    return {
        "website": website,
        "product": product,
        "rating": rating,
        "feedback": feedback,
        "ai_summary_user": feedback[:120],
        "ai_suggestions_user": ["Synthetic suggestion 1", "Synthetic suggestion 2"],
        "ai_summary_vendor": feedback[:120],
        "ai_suggestions_vendor": ["Synthetic vendor note"],
        "classification": classification,
    }


def build_dataset() -> List[dict]:
    docs: List[dict] = []
    now = datetime.now(timezone.utc)
    ts = now

    def add(doc):
        nonlocal ts
        doc["created_at"] = ts
        ts -= timedelta(minutes=5)
        docs.append(doc)

    # Alpha: high ratings, genuine
    alpha_feedbacks = [
        "Loved the alpha phone, smooth and reliable.",
        "Alpha case fits perfectly and feels premium.",
        "Alpha charge is fast and dependable.",
        "Great experience with alpha products.",
        "Alpha phone camera is excellent.",
    ]
    for fb in alpha_feedbacks:
        add(base_doc("alpha-shop", "alpha-phone", 5, fb, "genuine"))
    for fb in alpha_feedbacks:
        add(base_doc("alpha-shop", "alpha-case", 4, fb + " Nice design.", "genuine"))
    for fb in alpha_feedbacks:
        add(base_doc("alpha-shop", "alpha-charge", 5, fb + " Battery lasts long.", "genuine"))

    # Beta mouse: low rated, product issues
    beta_mouse_feedbacks = [
        "beta mouse is laggy and unresponsive.",
        "beta mouse clicks fail often.",
        "beta mouse feels cheap and drags.",
        "beta mouse stopped working quickly.",
    ]
    for fb in beta_mouse_feedbacks:
        add(base_doc("beta-store", "beta-mouse", 1, fb, "product_issue"))
        add(base_doc("beta-store", "beta-mouse", 2, fb + " Needs fixes.", "product_issue"))

    # Beta band (as requested) mention expensive twice
    beta_band_feedbacks = [
        "beta band is expensive and honestly too expensive for the features.",
        "beta band feels expensive expensive with little value.",
    ]
    for fb in beta_band_feedbacks:
        add(base_doc("beta-store", "beta-band", 2, fb, "product_issue"))

    # Beta laptop / bag mixed
    beta_other = [
        ("beta-store", "beta-laptop", 3, "beta laptop runs warm but usable.", "product_issue"),
        ("beta-store", "beta-bag", 4, "beta bag is sturdy and spacious.", "genuine"),
    ]
    for site, prod, rating, fb, cls in beta_other:
        add(base_doc(site, prod, rating, fb, cls))

    # Gamma delivery issues
    gamma_delivery = [
        "gamma watch arrived late, delivery issue.",
        "gamma band shipped late and box was damaged.",
        "gamma scale delivery delay annoyed me.",
        "gamma watch delayed delivery, packaging dented.",
        "gamma band delivery tracking was missing.",
    ]
    for fb in gamma_delivery:
        add(base_doc("gamma-mart", "gamma-watch", 2, fb, "delivery_issue"))
        add(base_doc("gamma-mart", "gamma-band", 3, fb + " Please fix shipping.", "delivery_issue"))

    # Minimal sarcasm
    sarcasm_fb = [
        "Yeah right, totally the best mouse ever (sarcasm).",
        "Sure, delivery was lightning fast... not really.",
    ]
    add(base_doc("beta-store", "beta-mouse", 2, sarcasm_fb[0], "sarcasm"))
    add(base_doc("gamma-mart", "gamma-band", 2, sarcasm_fb[1], "sarcasm"))

    # A few neutral/other
    other_fb = [
        ("alpha-shop", "alpha-phone", 3, "Decent but nothing special.", "other"),
        ("beta-store", "beta-laptop", 3, "Average performance, okay value.", "other"),
        ("gamma-mart", "gamma-scale", 3, "Works fine so far.", "other"),
    ]
    for site, prod, rating, fb, cls in other_fb:
        add(base_doc(site, prod, rating, fb, cls))

    # Ensure total >= 50
    while len(docs) < 50:
        add(base_doc("alpha-shop", "alpha-charge", 5, "Consistently great alpha experience.", "genuine"))

    return docs


async def main():
    client = AsyncIOMotorClient(MONGODB_URI)
    coll = client[DB_NAME][COLLECTION_NAME]
    docs = build_dataset()
    await coll.delete_many({"feedback": {"$regex": "^(Loved the alpha phone|beta mouse is laggy|beta band is expensive|gamma watch arrived late|Yeah right, totally the best mouse ever|Consistently great alpha experience)", "$options": "i"}})
    await coll.insert_many(docs)
    count = await coll.count_documents({})
    print(f"Inserted {len(docs)} docs. Collection now has {count} documents.")


if __name__ == "__main__":
    asyncio.run(main())
