"""AI features powered by Claude.

If the `anthropic` package is not installed, or no API credentials are
configured, every function here falls back to a simple offline version so
the app still works.
"""

import json
import os
import re
from datetime import date, timedelta

from tracker import CATEGORIES, guess_category

MODEL = os.environ.get("EXPENSE_AI_MODEL", "claude-opus-5-5")

try:
    import anthropic
except ImportError:  # app still works without the SDK
    anthropic = None

_client = None


def ai_available():
    """True if the SDK is installed and credentials look configured."""
    if anthropic is None:
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _ask_claude(system, prompt, schema=None, effort="low", max_tokens=4000):
    """Send one request to Claude. Returns parsed JSON if a schema is given,
    otherwise text. Returns None on any API problem so callers can fall back."""
    output_config = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        response = _get_client().beta.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config=output_config,
            # If the model declines, let the API retry on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIConnectionError:
        print("  (AI unavailable: network error — using offline mode)")
        return None
    except anthropic.AuthenticationError:
        print("  (AI unavailable: invalid API key — using offline mode)")
        return None
    except anthropic.RateLimitError:
        print("  (AI unavailable: rate limited — using offline mode)")
        return None
    except anthropic.APIStatusError as e:
        print(f"  (AI error {e.status_code} — using offline mode)")
        return None

    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if schema is None:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# 1. Natural-language expense entry
# ---------------------------------------------------------------------------

EXPENSE_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "number"},
        "category": {"type": "string", "enum": CATEGORIES},
        "description": {"type": "string"},
        "date": {"type": "string", "description": "YYYY-MM-DD"},
    },
    "required": ["amount", "category", "description", "date"],
    "additionalProperties": False,
}


def parse_expense(text, today=None):
    """Turn text like 'spent 12.50 on pizza yesterday' into an expense dict.

    Returns a dict with amount/category/description/date, or None if no
    amount could be found.
    """
    today = today or date.today()
    if ai_available():
        result = _ask_claude(
            system=(
                "You extract a single expense from the user's message. "
                f"Today's date is {today.isoformat()}. Resolve relative dates "
                "like 'yesterday' or 'last Friday' to YYYY-MM-DD; use today "
                "if no date is mentioned. Keep the description short "
                "(a few words). Choose the best category from the list."
            ),
            prompt=text,
            schema=EXPENSE_SCHEMA,
        )
        if result and result.get("amount", 0) > 0:
            return result
    return _parse_expense_offline(text, today)


def _parse_expense_offline(text, today):
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    amount = float(match.group(1))

    when = today
    lowered = text.lower()
    if "yesterday" in lowered:
        when = today - timedelta(days=1)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if date_match:
        when = date.fromisoformat(date_match.group(0))

    # Description: drop the amount, the date and filler words.
    desc = text.replace(match.group(1), "")
    if date_match:
        desc = desc.replace(date_match.group(0), "")
    desc = re.sub(r"\b(i|spent|paid|on|for|yesterday|today|rs|usd|\$)\b",
                  " ", desc, flags=re.IGNORECASE)
    desc = re.sub(r"[^\w\s-]", " ", desc)
    desc = " ".join(desc.split()) or "expense"

    return {
        "amount": amount,
        "category": guess_category(desc),
        "description": desc,
        "date": when.isoformat(),
    }


# ---------------------------------------------------------------------------
# 2. Auto-categorization
# ---------------------------------------------------------------------------

CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": CATEGORIES}},
    "required": ["category"],
    "additionalProperties": False,
}


def categorize(description):
    """Pick the best category for a description."""
    if ai_available():
        result = _ask_claude(
            system="Classify the expense description into one category.",
            prompt=description,
            schema=CATEGORY_SCHEMA,
        )
        if result and result.get("category") in CATEGORIES:
            return result["category"]
    return guess_category(description)


# ---------------------------------------------------------------------------
# 3. Spending insights
# ---------------------------------------------------------------------------

def spending_insights(tracker):
    """Return short, practical advice about the user's spending."""
    if not tracker.expenses:
        return "No expenses yet — add some first!"

    data = {
        "by_category_all_time": tracker.summary_by_category(),
        "by_month": tracker.summary_by_month(),
        "budgets_this_month": {
            cat: {"spent": round(spent, 2), "limit": limit}
            for cat, (spent, limit) in tracker.budget_status().items()
        },
        "recent_expenses": tracker.list_expenses()[-30:],
    }

    if ai_available():
        text = _ask_claude(
            system=(
                "You are a friendly personal-finance assistant. Given the "
                "user's expense data as JSON, write 4-6 short bullet points: "
                "where most money goes, notable trends between months, any "
                "budgets that are exceeded or close, and 2-3 concrete, "
                "realistic ways to save. Use plain text, no markdown headers. "
                "Do not invent data that isn't present."
            ),
            prompt=json.dumps(data, indent=2),
            effort="medium",
        )
        if text:
            return text
    return _insights_offline(tracker)


def _insights_offline(tracker):
    lines = []
    total = tracker.total()
    by_cat = tracker.summary_by_category()
    top_cat, top_amt = next(iter(by_cat.items()))
    lines.append(f"- Total spent: {total:.2f} across {len(tracker.expenses)} expenses.")
    lines.append(f"- Biggest category: {top_cat} ({top_amt:.2f}, "
                 f"{top_amt / total * 100:.0f}% of spending).")

    months = list(tracker.summary_by_month().items())
    if len(months) >= 2:
        (m1, a1), (m2, a2) = months[-2], months[-1]
        change = "up" if a2 > a1 else "down"
        lines.append(f"- Spending in {m2} is {change} from {m1} "
                     f"({a1:.2f} -> {a2:.2f}).")

    for cat in tracker.over_budget():
        spent, limit = tracker.budget_status()[cat]
        lines.append(f"- Over budget on {cat}: {spent:.2f} / {limit:.2f}.")

    lines.append("- Tip: set a monthly budget for your biggest category "
                 "to keep it in check.")
    lines.append("(Set ANTHROPIC_API_KEY for AI-powered insights.)")
    return "\n".join(lines)
