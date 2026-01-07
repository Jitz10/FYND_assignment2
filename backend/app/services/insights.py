import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from .analytics import compute_analytics_summary
from .database import get_database

load_dotenv()

_cache: Dict[str, Dict[str, Any]] = {}
_lock = asyncio.Lock()


def _filter_key(filters: Dict[str, Any]) -> str:
    return "|".join([str(filters.get("website", "")), str(filters.get("product", "")), str(filters.get("classification", ""))])


async def _latest_review_ts() -> Optional[str]:
    db = get_database()
    doc = await db["reviews"].find().sort("created_at", -1).limit(1).to_list(1)
    if not doc:
        return None
    ts = doc[0].get("created_at")
    if isinstance(ts, datetime):
        return ts.isoformat() + "Z"
    return str(ts)


async def generate_insights(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    filters = filters or {}
    key = _filter_key(filters)
    latest_ts = await _latest_review_ts()

    async with _lock:
        cached = _cache.get(key)
        if cached and cached.get("source_last_review_at") == latest_ts:
            return cached

    summary = await compute_analytics_summary(filters)

    generated_at = datetime.utcnow().isoformat() + "Z"
    text, recs = await _ai_insights(summary, filters)

    payload = {
        "summary": text,
        "recommendations": recs,
        "generated_at": generated_at,
        "source_last_review_at": latest_ts,
        "filters": filters,
    }
    async with _lock:
        _cache[key] = payload
    return payload


async def _ai_insights(summary: Dict[str, Any], filters: Dict[str, Any]):
    api_key = os.getenv("GROQ_API_KEY")
    filtered = {k: v for k, v in filters.items() if v}

    context = (
        f"Total reviews: {summary.get('total_reviews', 0)}\n"
        f"Average rating: {summary.get('avg_rating', 0)}\n"
        f"Top classification counts: {summary.get('classification_counts', {})}\n"
        f"Top website breakdown: {summary.get('website_breakdown', [])[:3]}\n"
        f"Top product breakdown: {summary.get('product_breakdown', [])[:3]}\n"
        f"Filters: {filtered or 'none'}"
    )

    prompt = (
        "You are an analytics copilot. Given metrics, produce a short, non-redundant insight (1-2 sentences) "
        "and 3 concise action recommendations. Keep it business-focused and avoid repeating raw numbers."
        "\n\nMetrics:\n" + context + "\n\nReturn JSON with keys 'insight' (string) and 'actions' (array of 3 short strings)."
    )

    if api_key:
        try:
            from groq import Groq  # type: ignore

            client = Groq(api_key=api_key)
            model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return concise analytics insight."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            import json

            data = json.loads(content)
            insight = str(data.get("insight", ""))
            actions = list(data.get("actions", []))[:3]
            if insight:
                return insight, actions
        except Exception:
            pass

    # heuristic fallback
    total = summary.get("total_reviews", 0)
    avg = summary.get("avg_rating", 0)
    top_class = "other"
    cc = summary.get("classification_counts", {}) or {}
    if cc:
        top_class = max(cc.items(), key=lambda x: x[1])[0]

    insight = f"{total} reviews with avg rating {avg}. Top theme: {top_class}. Filters: {filtered or 'none'}."
    actions = [
        "Dig into the top theme and address root causes",
        "Highlight wins from high-rated segments",
        "Track changes after fixes and monitor rating trend",
    ]
    return insight, actions
