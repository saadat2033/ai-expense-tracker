# AI Expense Tracker

A command-line expense tracker in Python with AI features powered by Claude.

## Features

- **Add, view, edit and delete expenses** — saved to `expenses.json`, so nothing is lost when you quit
- **Plain-English entry (AI)** — type `spent 12.50 on pizza yesterday` and it fills in the amount, category, description and date
- **Auto-categorization (AI)** — suggests a category from the description
- **Filters** — by category and/or month
- **Summaries** — totals by category (with a bar chart) and by month
- **Monthly budgets** — per category, with warnings at 80% and when you go over
- **AI spending insights** — where your money goes, trends, and ways to save
- **Export to CSV**

Works without an API key too: the AI features fall back to simple keyword rules.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here   # optional, enables AI features
python main.py
```

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Enables AI features |
| `EXPENSE_AI_MODEL` | `claude-opus-5-5` | Claude model to use |
| `EXPENSES_FILE` | `expenses.json` | Where expenses are stored |

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Interactive menu |
| `tracker.py` | Storage, CRUD, summaries, budgets, CSV export |
| `ai.py` | Claude-powered parsing, categorization, insights (with offline fallbacks) |
| `tests/` | Unit tests — run with `python -m unittest discover -s tests` |
