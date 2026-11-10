"""AI Expense Tracker — command-line app.

Run:  python main.py
"""

from ai import ai_available, categorize, parse_expense, spending_insights
from tracker import CATEGORIES, ExpenseTracker


def ask(prompt, default=None):
    value = input(prompt).strip()
    return value if value else default


def print_expenses(expenses):
    if not expenses:
        print("  No expenses found.")
        return
    print(f"  {'ID':>4}  {'Date':<10}  {'Amount':>10}  {'Category':<13}  Description")
    print("  " + "-" * 64)
    for e in expenses:
        print(f"  {e['id']:>4}  {e['date']:<10}  {e['amount']:>10.2f}  "
              f"{e['category']:<13}  {e['description']}")
    print("  " + "-" * 64)
    print(f"  {'Total':>28}  {sum(e['amount'] for e in expenses):.2f}")


def warn_budget(tracker, expense):
    month = expense["date"][:7]
    status = tracker.budget_status(month).get(expense["category"])
    if status:
        spent, limit = status
        if spent > limit:
            print(f"  ! Over your {expense['category']} budget for {month}: "
                  f"{spent:.2f} / {limit:.2f}")
        elif spent > 0.8 * limit:
            print(f"  ! {expense['category']} budget is {spent / limit:.0%} used "
                  f"({spent:.2f} / {limit:.2f})")


def add_manual(tracker):
    try:
        amount = float(ask("  Amount: "))
    except (TypeError, ValueError):
        print("  Invalid amount.")
        return
    description = ask("  Description: ", "")
    suggestion = categorize(description) if description else "Other"
    print(f"  Categories: {', '.join(CATEGORIES)}")
    category = ask(f"  Category [{suggestion}]: ", suggestion)
    when = ask("  Date YYYY-MM-DD [today]: ")
    try:
        expense = tracker.add_expense(amount, category, description, when)
    except ValueError as e:
        print(f"  Error: {e}")
        return
    print(f"  Added #{expense['id']}: {expense['amount']:.2f} "
          f"{expense['category']} — {expense['description']} ({expense['date']})")
    warn_budget(tracker, expense)


def add_natural(tracker):
    text = ask("  Describe it (e.g. 'spent 12.50 on pizza yesterday'): ", "")
    parsed = parse_expense(text)
    if not parsed:
        print("  Couldn't find an amount in that. Try again.")
        return
    print(f"  Understood: {parsed['amount']:.2f} | {parsed['category']} | "
          f"{parsed['description']} | {parsed['date']}")
    if ask("  Save it? [Y/n]: ", "y").lower().startswith("n"):
        print("  Cancelled.")
        return
    try:
        expense = tracker.add_expense(parsed["amount"], parsed["category"],
                                      parsed["description"], parsed["date"])
    except ValueError as e:
        print(f"  Error: {e}")
        return
    print(f"  Added #{expense['id']}.")
    warn_budget(tracker, expense)


def view(tracker):
    category = ask("  Filter by category (blank = all): ")
    month = ask("  Filter by month YYYY-MM (blank = all): ")
    print_expenses(tracker.list_expenses(category=category, month=month))


def read_id():
    try:
        return int(ask("  Expense ID: "))
    except (TypeError, ValueError):
        print("  Invalid ID.")
        return None


def edit(tracker):
    expense_id = read_id()
    if expense_id is None:
        return
    expense = tracker.get_expense(expense_id)
    if expense is None:
        print("  Not found.")
        return
    print("  Press Enter to keep the current value.")
    changes = {
        "amount": ask(f"  Amount [{expense['amount']}]: "),
        "category": ask(f"  Category [{expense['category']}]: "),
        "description": ask(f"  Description [{expense['description']}]: "),
        "date": ask(f"  Date [{expense['date']}]: "),
    }
    try:
        tracker.update_expense(expense_id, **changes)
        print("  Updated.")
    except ValueError as e:
        print(f"  Error: {e}")


def delete(tracker):
    expense_id = read_id()
    if expense_id is None:
        return
    expense = tracker.get_expense(expense_id)
    if expense is None:
        print("  Not found.")
        return
    if ask(f"  Delete '{expense['description']}' ({expense['amount']:.2f})? [y/N]: ",
           "n").lower().startswith("y"):
        tracker.delete_expense(expense_id)
        print("  Deleted.")


def summary(tracker):
    month = ask("  Month YYYY-MM (blank = all time): ")
    by_cat = tracker.summary_by_category(month)
    if not by_cat:
        print("  No expenses.")
        return
    total = sum(by_cat.values())
    print("\n  By category:")
    for cat, amount in by_cat.items():
        bar = "#" * int(amount / total * 30)
        print(f"  {cat:<13} {amount:>10.2f}  {bar}")
    print(f"  {'Total':<13} {total:>10.2f}")
    if not month:
        print("\n  By month:")
        for m, amount in tracker.summary_by_month().items():
            print(f"  {m:<13} {amount:>10.2f}")


def budgets(tracker):
    status = tracker.budget_status()
    if status:
        print("  This month's budgets:")
        for cat, (spent, limit) in status.items():
            flag = "  OVER" if spent > limit else ""
            print(f"  {cat:<13} {spent:>10.2f} / {limit:.2f}{flag}")
    category = ask("  Set budget for category (blank = skip): ")
    if not category:
        return
    try:
        tracker.set_budget(category, ask("  Monthly limit: "))
        print("  Budget saved.")
    except (TypeError, ValueError):
        print("  Invalid amount.")


def export(tracker):
    path = ask("  File name [expenses.csv]: ", "expenses.csv")
    tracker.export_csv(path)
    print(f"  Exported {len(tracker.expenses)} expenses to {path}")


MENU = [
    ("Add expense", add_manual),
    ("Add expense in plain English (AI)", add_natural),
    ("View expenses", view),
    ("Edit expense", edit),
    ("Delete expense", delete),
    ("Summary", summary),
    ("Budgets", budgets),
    ("AI spending insights", lambda t: print(spending_insights(t))),
    ("Export to CSV", export),
]


def main():
    tracker = ExpenseTracker()
    mode = "AI enabled" if ai_available() else "offline mode (set ANTHROPIC_API_KEY for AI)"
    print(f"\n=== AI Expense Tracker === [{mode}]")
    while True:
        print()
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}. {label}")
        print("  0. Exit")
        choice = ask("Choose: ", "")
        if choice == "0":
            print("Goodbye!")
            break
        if choice.isdigit() and 1 <= int(choice) <= len(MENU):
            print()
            MENU[int(choice) - 1][1](tracker)
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
