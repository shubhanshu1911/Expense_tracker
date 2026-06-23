# Spec: Add Expense

## Overview
This feature lets a logged-in user submit a new expense via a form. It converts the
existing stub `GET /expenses/add` into a full `GET` + `POST` route, adds an
`add_expense()` DB helper, and creates the `add_expense.html` template. On
successful submission the user is redirected to `/profile` so they can see the new
expense appear in their transaction history immediately.

## Depends on
- Step 03 — Login/Logout (session handling)
- Step 05 — Profile Routes (profile page the user is redirected to)
- Step 01 — Database Setup (expenses table already created in `init_db()`)

## Routes
- `GET /expenses/add` — render the Add Expense form — logged-in only
- `POST /expenses/add` — validate and insert the expense, then redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The `expenses` table already has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

A new DB helper function `add_expense(user_id, amount, category, date, description)`
must be added to `database/db.py`.

## Templates
- **Create:** `templates/add_expense.html` — form with fields: amount, category (dropdown), date, description (optional)
- **Modify:** none

## Files to change
- `app.py` — replace stub `add_expense` route with GET + POST implementation
- `database/db.py` — add `add_expense()` helper
- `app.py` import line — import `add_expense` from `database.db`

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Unauthenticated requests to either route must redirect to `/login`
- `amount` must be a positive number; reject zero or negative values
- `category` must be one of the fixed allowed values: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- `date` must be a valid date in `YYYY-MM-DD` format; reject missing or malformed dates
- `description` is optional — store `None` / empty string as-is, do not require it
- On validation failure, re-render the form with an error message and preserve the user's input
- On success, flash a confirmation message and redirect to `url_for("profile")`
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done
- [ ] `GET /expenses/add` renders a form with fields: amount, category, date, description
- [ ] Submitting the form with valid data inserts a row into `expenses` and redirects to `/profile`
- [ ] The new expense is visible in the transaction list on the profile page after redirect
- [ ] Submitting with a missing or non-positive amount shows a validation error and re-renders the form
- [ ] Submitting with an invalid category (e.g. direct POST with a bad value) shows a validation error
- [ ] Submitting with a missing or malformed date shows a validation error
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] A flash message confirms successful submission on the profile page
