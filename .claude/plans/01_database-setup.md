# Plan: 01 — Database Setup

## Context

`database/db.py` is currently a stub (only comments). All future features —
authentication, expense tracking, profile — depend on a working SQLite layer.
This step implements the three required helpers and wires them into `app.py`
so the database is ready before any request is served.

---

## Files to change

| File | What changes |
|---|---|
| `database/db.py` | Implement `get_db()`, `init_db()`, `seed_db()` |
| `app.py` | Import the three helpers; call `init_db()` + `seed_db()` at startup |

No new files. No new pip packages (`sqlite3` is stdlib; `werkzeug` is already installed).

---

## `database/db.py` — implementation

### `get_db()`

- Resolves `spendly.db` relative to project root via `__file__`
- Sets `row_factory = sqlite3.Row` for dict-like column access
- Runs `PRAGMA foreign_keys = ON` on every connection

### `init_db()`

Creates both tables with `CREATE TABLE IF NOT EXISTS` — safe to call on every startup.

**users:** id, name, email (UNIQUE), password_hash, created_at  
**expenses:** id, user_id (FK → users.id), amount (REAL), category, date (YYYY-MM-DD), description, created_at

### `seed_db()`

Guard: if `users` table already has rows → return early (no duplicates).

Demo user: `Demo User / demo@spendly.com / demo123` (password hashed via `werkzeug.security.generate_password_hash`)

8 sample expenses across all 7 categories (Food gets a second entry), dates in June 2026.

---

## `app.py` — changes

```python
from database.db import get_db, init_db, seed_db
```

Startup calls inside `if __name__ == "__main__":`:

```python
if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
```

---

## Verification

1. `python app.py` — starts on port 5001, no errors
2. `spendly.db` exists in project root
3. `SELECT * FROM users` → 1 row; `SELECT COUNT(*) FROM expenses` → 8
4. Second run of `python app.py` → no duplicate rows
