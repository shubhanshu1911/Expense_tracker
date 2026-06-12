# Spec: Login and Logout

## Overview
Implement session-based authentication so registered users can sign in and sign out of Spendly. This step upgrades the existing stub `GET /login` into a fully functional form that accepts a POST, verifies credentials against the database, and writes the authenticated user's id and name into Flask's `session`. The `GET /logout` stub is replaced with a route that clears the session and redirects to the landing page. After this step, the app knows who is logged in, and the navbar reflects that state.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user()`, `users` rows exist)

## Routes
- `GET /login` — render login form — public (already exists as stub, upgrade to support GET + POST)
- `POST /login` — verify credentials, set session, redirect to `/profile` — public
- `GET /logout` — clear session, redirect to `/` — logged-in (currently returns raw stub string, replace it)

## Database changes
No new tables or columns. The existing `users` table covers all requirements.

A new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — queries `users` by email, returns a `sqlite3.Row` (with columns `id`, `name`, `email`, `password_hash`) or `None` if not found.

## Templates
- **Modify**: `templates/login.html`
  - Change the form `action` to `url_for('login')` with `method="post"` (currently hardcodes `/login`)
  - Ensure the error block works with the `error` variable passed from the route (already present)
  - No structural redesign needed — keep all existing visual design

- **Modify**: `templates/base.html`
  - Update the `nav-links` block to show context-aware links:
    - If `session.user_id` is set: show user's name (or "My account") linking to `/profile` and a "Sign out" link to `url_for('logout')`
    - If not logged in: show existing "Sign in" and "Get started" links

## Files to change
- `app.py` — upgrade `login()` to handle `GET` and `POST`; implement `logout()` to clear session
- `database/db.py` — add `get_user_by_email()` helper
- `templates/login.html` — fix form action to use `url_for('login')`
- `templates/base.html` — make navbar session-aware

## Files to create
None.

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (already installed) and Flask's built-in `session`, `redirect`, `url_for`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Verify passwords with `werkzeug.security.check_password_hash` — never compare plaintext
- Store only `session['user_id']` (int) and `session['user_name']` (str) in the session — nothing else
- `app.secret_key` is already set in `app.py` — do not change it
- Server-side validation for login must check:
  1. Both `email` and `password` fields are non-empty
  2. A user with that email exists in the database
  3. The provided password matches the stored hash
- On any validation failure, re-render `login.html` with an `error` variable — use a generic message ("Invalid email or password") that does not reveal which field was wrong
- On successful login, set `session['user_id']` and `session['user_name']`, then `redirect(url_for('profile'))`
- `logout()` must call `session.clear()` then `redirect(url_for('landing'))`
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done
- [ ] `GET /login` renders the login form without errors
- [ ] Submitting valid credentials sets the session and redirects to `/profile` (stub page is fine)
- [ ] Submitting an unknown email re-renders the form with a generic error, no session set
- [ ] Submitting a wrong password re-renders the form with the same generic error, no session set
- [ ] Submitting with any empty field re-renders the form with a validation error
- [ ] `GET /logout` clears the session and redirects to the landing page `/`
- [ ] After logout, `/logout` again (no session) still redirects to `/` without error
- [ ] Navbar shows "Sign in" / "Get started" when not logged in
- [ ] Navbar shows user name and "Sign out" link when logged in
- [ ] `session` never contains the password or password hash
