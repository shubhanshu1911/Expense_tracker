# Spec: Delete Expense

## Overview
This feature lets a logged-in user permanently remove one of their own expenses from Spendly. It replaces the stub `GET /expenses/<id>/delete` route (currently returning a placeholder string) with a real confirmation flow: the user clicks "Delete" from their profile transaction table, sees a confirmation page showing the expense details, and confirms before the record is removed from the database. This is the last of the three expense-management steps (add → edit → delete), completing full CRUD on expenses.

## Depends on
- Step 01 (database setup) — `expenses` table and `get_db()`
- Step 05 (profile routes) — `get_expense_by_id()` in `database/queries.py`
- Step 07 (add expense) — `EXPENSE_CATEGORIES`, form-rendering conventions
- Step 08 (edit expense) — ownership-check pattern (`get_expense_by_id(expense_id, user_id)` + `abort(404)`), GET/POST-on-same-route pattern

## Routes
- `GET /expenses/<int:id>/delete` — show a confirmation page with the expense's date, category, amount, and description — logged-in only
- `POST /expenses/<int:id>/delete` — delete the expense (only if it belongs to the current user), flash a success message, redirect to `/profile` — logged-in only

If the expense does not exist or does not belong to the current user, `abort(404)`.

## Database changes
No database changes. The `expenses` table (see `database/db.py`) already has everything needed. Add one new helper function to `database/db.py`:

```python
def delete_expense(expense_id, user_id):
    db = get_db()
    cursor = db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    db.commit()
    deleted = cursor.rowcount
    db.close()
    return deleted
```

This mirrors the existing `update_expense()` pattern: scoped by `user_id`, returns the row count so the route can `abort(404)` if nothing was deleted.

## Templates
- **Create:** `templates/delete_expense.html` — confirmation page extending `base.html`. Shows the expense's date, category badge, amount, and description (read-only), a "Confirm Delete" button (POSTs to the same URL), and a "Cancel" link back to `/profile`.
- **Modify:** `templates/profile.html` — in the transaction table's Actions column (around line 106-108), add a "Delete" link next to the existing "Edit" link, pointing to `url_for('delete_expense', id=tx.id)`.

## Files to change
- `app.py` — replace the `delete_expense` stub with the real GET/POST implementation; import `delete_expense` from `database.db` and `get_expense_by_id` from `database.queries` (already imported)
- `database/db.py` — add `delete_expense()` helper
- `templates/profile.html` — add Delete link in the Actions column
- `.claude/CLAUDE.md` — update the routes table to mark `GET /expenses/<id>/delete` as implemented

## Files to create
- `templates/delete_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a for this feature, but keep in mind for any touched auth code)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Reuse the existing ownership-check pattern from `edit_expense`: fetch via `get_expense_by_id(id, session["user_id"])`, `abort(404)` if `None`
- Do not use a bare `GET` link to directly perform the deletion — the delete must happen via `POST` (a form/button), not a plain `<a href>`, to avoid destructive GET requests
- Keep `delete_expense` in `database/db.py`, not inline SQL in `app.py`

## Definition of done
- [ ] Logged out, visiting `/expenses/1/delete` redirects to `/login`
- [ ] Logged in, clicking "Delete" on a transaction in `/profile` navigates to a confirmation page showing that expense's correct date, category, amount, and description
- [ ] On the confirmation page, clicking "Cancel" returns to `/profile` without deleting anything
- [ ] On the confirmation page, clicking "Confirm Delete" removes the expense, shows a success flash message, and redirects to `/profile`
- [ ] The deleted expense no longer appears in the transaction table or affects the summary stats / category breakdown on `/profile`
- [ ] Visiting `/expenses/<id>/delete` for an expense belonging to another user returns 404
- [ ] Visiting `/expenses/<id>/delete` for a non-existent expense id returns 404
- [ ] No inline SQL in `app.py`; deletion goes through `delete_expense()` in `database/db.py`
