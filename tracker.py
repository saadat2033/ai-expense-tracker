"""Core expense-tracking logic: storage, CRUD, summaries and budgets.

Everything here is plain Python (no AI, no network) so it is easy to test.
"""

import csv
import json
import os
from datetime import date, datetime

DEFAULT_FILE = os.environ.get("EXPENSES_FILE", "expenses.json")

CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Health",
    "Education",
    "Travel",
    "Other",
]

# Simple keyword rules used to guess a category when AI is not available.
KEYWORDS = {
    "Food": ["lunch", "dinner", "breakfast", "coffee", "grocer", "restaurant",
             "pizza", "burger", "snack", "food", "cafe", "tea", "meal"],
    "Transport": ["bus", "taxi", "uber", "lyft", "train", "metro", "fuel",
                  "gas", "petrol", "parking", "ticket", "careem", "rickshaw"],
    "Shopping": ["clothes", "shoes", "amazon", "shirt", "gift", "shop",
                 "electronics", "phone case"],
    "Bills": ["rent", "electric", "water", "internet", "wifi", "phone bill",
              "bill", "subscription", "insurance"],
    "Entertainment": ["movie", "cinema", "netflix", "spotify", "game",
                      "concert", "party"],
    "Health": ["doctor", "medicine", "pharmacy", "gym", "hospital", "dentist"],
    "Education": ["book", "course", "tuition", "school", "udemy", "class"],
    "Travel": ["hotel", "flight", "airbnb", "trip", "vacation"],
}


def guess_category(description):
    """Guess a category from the description using keyword matching."""
    text = description.lower()
    for category, words in KEYWORDS.items():
        if any(word in text for word in words):
            return category
    return "Other"


def normalize_category(category):
    """Match a category case-insensitively against the known list."""
    for known in CATEGORIES:
        if known.lower() == str(category).strip().lower():
            return known
    return "Other"


def parse_date(value):
    """Accept YYYY-MM-DD (or empty for today) and return an ISO date string."""
    if not value:
        return date.today().isoformat()
    return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()


class ExpenseTracker:
    def __init__(self, path=DEFAULT_FILE):
        self.path = path
        self.expenses = []
        self.budgets = {}  # category -> monthly limit
        self.load()

    # ---------- storage ----------
    def load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.expenses = data.get("expenses", [])
        self.budgets = data.get("budgets", {})

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"expenses": self.expenses, "budgets": self.budgets},
                      f, indent=2)

    def _next_id(self):
        return max((e["id"] for e in self.expenses), default=0) + 1

    # ---------- CRUD ----------
    def add_expense(self, amount, category, description, when=None):
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be greater than 0.")
        expense = {
            "id": self._next_id(),
            "amount": round(amount, 2),
            "category": normalize_category(category),
            "description": description.strip(),
            "date": parse_date(when),
        }
        self.expenses.append(expense)
        self.save()
        return expense

    def get_expense(self, expense_id):
        for expense in self.expenses:
            if expense["id"] == expense_id:
                return expense
        return None

    def update_expense(self, expense_id, **changes):
        expense = self.get_expense(expense_id)
        if expense is None:
            return None
        if changes.get("amount") is not None:
            amount = float(changes["amount"])
            if amount <= 0:
                raise ValueError("Amount must be greater than 0.")
            expense["amount"] = round(amount, 2)
        if changes.get("category"):
            expense["category"] = normalize_category(changes["category"])
        if changes.get("description"):
            expense["description"] = changes["description"].strip()
        if changes.get("date"):
            expense["date"] = parse_date(changes["date"])
        self.save()
        return expense

    def delete_expense(self, expense_id):
        expense = self.get_expense(expense_id)
        if expense is None:
            return False
        self.expenses.remove(expense)
        self.save()
        return True

    def list_expenses(self, category=None, month=None):
        """Return expenses, optionally filtered by category and/or month (YYYY-MM)."""
        result = self.expenses
        if category:
            category = normalize_category(category)
            result = [e for e in result if e["category"] == category]
        if month:
            result = [e for e in result if e["date"].startswith(month)]
        return sorted(result, key=lambda e: (e["date"], e["id"]))

    # ---------- reports ----------
    def total(self, expenses=None):
        expenses = self.expenses if expenses is None else expenses
        return round(sum(e["amount"] for e in expenses), 2)

    def summary_by_category(self, month=None):
        totals = {}
        for e in self.list_expenses(month=month):
            totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]
        return dict(sorted(((k, round(v, 2)) for k, v in totals.items()),
                           key=lambda kv: kv[1], reverse=True))

    def summary_by_month(self):
        totals = {}
        for e in self.expenses:
            month = e["date"][:7]
            totals[month] = totals.get(month, 0) + e["amount"]
        return {k: round(v, 2) for k, v in sorted(totals.items())}

    # ---------- budgets ----------
    def set_budget(self, category, limit):
        limit = float(limit)
        if limit <= 0:
            raise ValueError("Budget must be greater than 0.")
        self.budgets[normalize_category(category)] = round(limit, 2)
        self.save()

    def budget_status(self, month=None):
        """Return {category: (spent, limit)} for categories that have a budget."""
        month = month or date.today().strftime("%Y-%m")
        spent = self.summary_by_category(month)
        return {cat: (spent.get(cat, 0), limit)
                for cat, limit in self.budgets.items()}

    def over_budget(self, month=None):
        return [cat for cat, (spent, limit) in self.budget_status(month).items()
                if spent > limit]

    # ---------- export ----------
    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "date", "amount", "category", "description"])
            writer.writeheader()
            for e in self.list_expenses():
                writer.writerow({k: e[k] for k in writer.fieldnames})
        return path
