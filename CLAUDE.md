# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What does this project do?

**Spendly** is a personal expense tracker web app. Users register, log in, and record expenses with a category, amount, date, and description. The app shows spending breakdowns and monthly summaries so users can understand where their money goes.

## Tech stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.1 (Python) |
| Database | SQLite (via Python's `sqlite3`) |
| Templating | Jinja2 (bundled with Flask) |
| Frontend | Vanilla CSS + JavaScript |
| Testing | pytest + pytest-flask |

No ORM — raw SQL with `sqlite3.Row` for dict-like row access.

## Running the app

```bash
# activate virtualenv first
source VENV/bin/activate

# run dev server (port 5001, debug mode on)
python3 app.py
```

## Running tests

```bash
pytest                        # all tests
pytest tests/test_auth.py     # single file
pytest -k "test_login"        # single test by name
```

## Project structure

```
app.py              # Flask app — all routes defined here
database/
  db.py             # get_db(), init_db(), seed_db() — raw SQLite helpers
  __init__.py
templates/
  base.html         # shared navbar + footer; all pages extend this
  landing.html      # marketing/hero page
  login.html        # POST /login
  register.html     # POST /register
static/
  css/style.css
  js/main.js
```

## Architecture notes

- All routes live in `app.py` — there are no Blueprints.
- `database/db.py` is the only place that touches SQLite. It exposes three functions: `get_db()` (returns a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`), `init_db()` (creates tables), and `seed_db()` (inserts dev data).
- `base.html` is the layout shell. Every page template uses `{% extends "base.html" %}` and fills `{% block content %}`.
- The `{% if error %}` block in `login.html` and `register.html` expects the route to pass an `error=` variable in `render_template` on failure.

## Implementation roadmap (step stubs already in app.py)

Several routes currently return placeholder strings. The intended build order is:

1. `database/db.py` — SQLite setup
2. `POST /register` — create user (hash password with `werkzeug.security`)
3. `POST /login` / `GET /logout` — session management
4. `GET /profile` — user profile page
5. `GET /expenses` — list expenses
6. Filtering by date range
7. `POST /expenses/add`
8. `POST /expenses/<id>/edit`
9. `GET /expenses/<id>/delete`
