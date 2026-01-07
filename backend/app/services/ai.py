import json
import os
import re
from typing import List, Tuple

from dotenv import load_dotenv

load_dotenv()

# Temporary catalog mapping websites to products
CATALOG = {
    "alpha-shop": ["alpha-phone", "alpha-case", "alpha-charge"],
    "beta-store": ["beta-laptop", "beta-mouse", "beta-bag"],
    "gamma-mart": ["gamma-watch", "gamma-band", "gamma-scale"],
}


async def generate_summary_and_suggestions(
    rating: int, feedback: str, website: str, product: str
) -> Tuple[str, List[str], str, List[str], str]:
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        from groq import Groq  # type: ignore

        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        catalog_text = "\n".join(
            f"- {site}: {', '.join(items)}" for site, items in CATALOG.items()
        )
        prompt = (
            "You are an assistant for customer feedback insights. "
            "Given a star rating (1-5), review text, website, and product, return a JSON object with: "
            "'user_summary' (one concise sentence for the end-user), 'user_suggestions' (3-4 short actionable items for the user), "
            "'vendor_summary' (one concise sentence for the vendor), 'vendor_suggestions' (3-4 short actionable items for the vendor), and 'classification' "
            "(one of: product_issue, delivery_issue, sarcasm, genuine, other). Use 'genuine' for clearly positive, authentic praise (typically rating >= 4) with no sarcasm.\n\n"
            f"Rating: {rating}/5\nReview: {feedback}\nWebsite: {website}\nProduct: {product}\n\n"
            "Catalog (website -> products):\n"
            f"{catalog_text}\n\n"
            "Respond ONLY with JSON having keys 'user_summary', 'user_suggestions', 'vendor_summary', 'vendor_suggestions', 'classification'."
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return concise, business-friendly insights only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        print("AI response content:", content)
        data = _extract_json(content)
        if data and "user_summary" in data and "user_suggestions" in data:
            classification = str(data.get("classification", "other"))
            user_summary = str(data.get("user_summary", ""))
            user_suggestions = list(data.get("user_suggestions", []))[:4]
            vendor_summary = str(data.get("vendor_summary", user_summary))
            vendor_suggestions = list(data.get("vendor_suggestions", user_suggestions))[:4]
            return user_summary, user_suggestions, vendor_summary, vendor_suggestions, classification

        # If the AI response is malformed, fall back to heuristic to avoid 500s
        user_summary, user_suggestions, vendor_summary, vendor_suggestions, classification = _heuristic_summary(
            rating, feedback
        )
        return user_summary, user_suggestions, vendor_summary, vendor_suggestions, classification

    # Fallback only when no AI key is configured
    return _heuristic_summary(rating, feedback)


def _extract_json(text: str):
    """Try to parse a JSON object from a string, even if wrapped in text/code fences."""
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


def _heuristic_summary(rating: int, feedback: str) -> Tuple[str, List[str], str, List[str], str]:
    cleaned = " ".join(feedback.split())
    if len(cleaned) > 220:
        cleaned_short = cleaned[:210].rsplit(" ", 1)[0] + "…"
    else:
        cleaned_short = cleaned

    if rating >= 5:
        tone = "extremely positive"
    elif rating == 4:
        tone = "positive"
    elif rating == 3:
        tone = "mixed"
    elif rating == 2:
        tone = "negative"
    else:
        tone = "very negative"

    summary = f"A {tone} {rating}/5 review: {cleaned_short}"
    vendor_summary = f"User sentiment is {tone} ({rating}/5). Key text: {cleaned_short}"

    if rating >= 5:
        user_suggestions = [
            "Keep enjoying and share what you love most",
            "Consider leaving a public review",
            "Check related accessories for added value",
        ]
        vendor_suggestions = [
            "Acknowledge praise publicly and maintain quality",
            "Highlight the loved features in marketing",
            "Invite referrals or testimonials",
        ]
    elif rating == 4:
        user_suggestions = [
            "Let us know any small issues you noticed",
            "Use tips/resources to get full value",
            "Share feedback to reach a perfect 5",
        ]
        vendor_suggestions = [
            "Address minor issues raised by users",
            "Monitor recurring themes to reach 5/5",
            "Improve onboarding or guidance materials",
        ]
    elif rating == 3:
        user_suggestions = [
            "Tell us specific pain points so we can fix them",
            "Try suggested tips to improve experience",
            "Expect follow-up from support",
        ]
        vendor_suggestions = [
            "Reach out to clarify pain points",
            "Prioritize quick wins to lift satisfaction",
            "Improve guidance/onboarding where users struggle",
        ]
    elif rating == 2:
        user_suggestions = [
            "We’re sorry—support will reach out to resolve",
            "Share specifics so we can fix them fast",
            "Accept a make-good while we address issues",
        ]
        vendor_suggestions = [
            "Contact the user to resolve issues",
            "Fix top friction points causing dissatisfaction",
            "Offer make-good (discount, support session)",
        ]
    else:
        user_suggestions = [
            "We’re escalating your concerns immediately",
            "Expect proactive follow-up after fixes",
            "Tell us the top blockers to prioritize",
        ]
        vendor_suggestions = [
            "Escalate critical issues immediately",
            "Perform root-cause analysis on failures",
            "Proactively follow up after remediation",
        ]

    classification = "other"

    return summary, user_suggestions[:4], vendor_summary, vendor_suggestions[:4], classification
