import os
import sqlite3

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spendly.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    db.commit()
    db.close()


def create_user(name, email, password):
    password_hash = generate_password_hash(password)
    db = get_db()
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return user_id


def insert_expense(user_id, amount, category, expense_date, description):
    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    db.commit()
    expense_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return expense_id


def get_user_by_email(email):
    db = get_db()
    user = db.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    db.close()
    return user


def seed_db():
    db = get_db()

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        db.close()
        return

    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    expenses = [
        (user_id, 850.00,  "Food",          "2026-06-01", "Groceries"),
        (user_id, 250.00,  "Transport",     "2026-06-03", "Monthly metro pass"),
        (user_id, 1200.00, "Bills",         "2026-06-05", "Electricity bill"),
        (user_id, 500.00,  "Health",        "2026-06-07", "Pharmacy"),
        (user_id, 399.00,  "Entertainment", "2026-06-08", "Streaming subscription"),
        (user_id, 2200.00, "Shopping",      "2026-06-10", "Clothes"),
        (user_id, 150.00,  "Other",         "2026-06-11", "Miscellaneous"),
        (user_id, 620.00,  "Food",          "2026-06-12", "Restaurant dinner"),
    ]
    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )

    db.commit()
    db.close()
