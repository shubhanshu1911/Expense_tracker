# Spec: Edit Expense

## Overview
This feature lets a logged-in user modify one of their existing expenses. It converts
the existing stub `GET /expenses/<id>/edit` into a full `GET` + `POST` route, adds DB
helpers to fetch a single expense and update it, and creates the `edit_expense.html`
template (a pre-filled version of the add-expense form). It also surfaces an **Edit**
link next to each row in the profile transaction table so users can reach the form.
Ownership is enforced: a user may only edit expenses they own. On success the user is
redirected to `/profile` to see the updated transaction, mirroring the add-expense flow
(Step 07).

## Depends on
- Step 01 — Database Setup (`expenses` table created in `init_db()`)
- Step 03 — Login/Logout (session handling)
- Step 05 — Profile Routes (profile page the user returns to, transaction list)
- Step 07 — Add Expense (shares form layout, validation rules, and category list)

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the expense's current values — logged-in only
- `POST /expenses/<int:id>/edit` — validate and update the expense, then redirect to `/profile` — logged-in only

Both routes replace the current stub `edit_expense(id)` in `app.py`. A request for an
expense that does not exist, or that belongs to another user, must `abort(404)`.

## Database changes
No new tables or columns. The `expenses` table already has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

Two DB helpers must be added:
- `get_expense_by_id(expense_id, user_id)` in `database/queries.py` — a read helper that
  returns the expense row only if it belongs to `user_id` (scoped by `user_id` in the
  `WHERE` clause), else `None`.
- `update_expense(expense_id, user_id, amount, category, date, description)` in
  `database/db.py` — a mutation helper that updates the row, scoped by both `id` and
  `user_id` so a user can never update another user's expense.

Additionally, `get_recent_transactions()` in `database/queries.py` must be updated to
also `SELECT id`, and the `profile` route's transaction dict must carry `id`, so the
profile template can build the per-row edit link.

## Templates
- **Create:** `templates/edit_expense.html` — same field set as `add_expense.html`
  (amount, category dropdown, date, optional description) but pre-filled with the
  expense's current values; form posts to `url_for('edit_expense', id=expense.id)`.
- **Modify:** `templates/profile.html` — add an **Edit** link/action per transaction row
  pointing to `url_for('edit_expense', id=tx.id)`.

## Files to change
- `app.py` — replace stub `edit_expense` route with GET + POST implementation; add
  `get_expense_by_id` and `update_expense` to the imports; add `id` to the transaction
  dict built in the `profile` route.
- `database/db.py` — add `update_expense()` helper.
- `database/queries.py` — add `get_expense_by_id()` helper; add `id` to the
  `SELECT` and returned dict in `get_recent_transactions()`.
- `templates/profile.html` — add per-row Edit link.

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (unchanged — no auth changes here, but the rule stands)
- Unauthenticated requests to either route must redirect to `/login`
- Ownership enforced: both the fetch and the update must be scoped by `user_id`; a
  missing or non-owned expense must `abort(404)` — never a bare string return
- Reuse the Step 07 validation rules exactly:
  - `amount` must be a positive number, `> 0` and `<= MAX_EXPENSE_AMOUNT`
  - `category` must be one of `EXPENSE_CATEGORIES`
  - `date` must be valid `YYYY-MM-DD`
  - `description` optional, `<= MAX_DESCRIPTION_LENGTH`, stored as `None` when empty
- On validation failure, re-render the edit form with an error message and preserve the
  user's submitted input (not the original DB values)
- On success, flash a confirmation message and redirect to `url_for("profile")`
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs
- Keep route functions single-responsibility; put all DB logic in `database/`

## Definition of done
- [ ] `GET /expenses/<id>/edit` renders a form pre-filled with that expense's amount, category, date, and description
- [ ] The profile transaction table shows an Edit link on each row that opens the correct expense's edit form
- [ ] Submitting the edit form with valid changes updates the row and redirects to `/profile`
- [ ] The updated values are visible in the profile transaction list after redirect
- [ ] A flash message confirms the successful update on the profile page
- [ ] Submitting with a missing/non-positive/too-large amount re-renders the form with an error and preserves input
- [ ] Submitting with an invalid category (direct POST) re-renders the form with an error
- [ ] Submitting with a missing or malformed date re-renders the form with an error
- [ ] Requesting `/expenses/<id>/edit` for a non-existent expense returns 404
- [ ] Requesting `/expenses/<id>/edit` for an expense owned by another user returns 404 (no data leak)
- [ ] Visiting either edit route while logged out redirects to `/login`
