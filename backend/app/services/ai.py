import asyncio
import json
import os
import re
from typing import List, Tuple

from dotenv import load_dotenv
load_dotenv()

async def generate_summary_and_suggestions(rating: int, feedback: str) -> Tuple[str, List[str]]:
    try:
        api_key = os.getenv("GROQ_API_KEY")
        #print(f"GROQ_API_KEY: {api_key}")
        if api_key:
            try:
                from groq import Groq  # type: ignore

                client = Groq(api_key=api_key)
                model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
                #print(f"Using Groq model: {model}")
                prompt = (
                    "You are an assistant for customer feedback insights. "
                    "Given a star rating (1-5) and review text, return a JSON object with: "
                    "'summary' (one concise sentence) and 'suggestions' (3-4 short, actionable items).\n\n"
                    f"Rating: {rating}/5\nReview: {feedback}\n\n"
                    "Respond ONLY with JSON having keys 'summary' and 'suggestions'."
                )
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Return concise, business-friendly insights only."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                print(f"Groq response: {resp}")
                content = (resp.choices[0].message.content or "").strip()
                data = _extract_json(content)
                if data and "summary" in data and "suggestions" in data:
                    return str(data["summary"]), list(data["suggestions"])[:4]
            except Exception:
                pass
    except Exception:
        pass

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


def _heuristic_summary(rating: int, feedback: str) -> Tuple[str, List[str]]:
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

    if rating >= 5:
        suggestions = [
            "Acknowledge the praise and keep consistency",
            "Identify what delighted the user and amplify it",
            "Invite a testimonial or referral",
        ]
    elif rating == 4:
        suggestions = [
            "Thank the user and address minor issues",
            "Monitor recurring themes to reach 5/5",
            "Offer tips or resources to enhance value",
        ]
    elif rating == 3:
        suggestions = [
            "Reach out to clarify pain points",
            "Prioritize quick wins to improve experience",
            "Provide guidance or better onboarding",
        ]
    elif rating == 2:
        suggestions = [
            "Contact the user to resolve issues",
            "Fix top friction points causing dissatisfaction",
            "Offer a make-good (discount, support session)",
        ]
    else:
        suggestions = [
            "Escalate and remediate critical issues immediately",
            "Conduct root-cause analysis on failures",
            "Proactively follow up after fixes",
        ]

    kw = cleaned.lower()
    if any(k in kw for k in ["slow", "lag", "performance", "loading"]):
        suggestions.append("Improve performance and loading responsiveness")
    elif any(k in kw for k in ["bug", "crash", "error", "issue"]):
        suggestions.append("Fix stability issues and add regression tests")
    elif any(k in kw for k in ["price", "cost", "expensive", "pricing"]):
        suggestions.append("Review pricing and communicate value more clearly")
    elif any(k in kw for k in ["support", "help", "service", "response"]):
        suggestions.append("Improve support responsiveness and resolution quality")

    return summary, suggestions[:4]
