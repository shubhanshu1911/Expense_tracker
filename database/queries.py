"""Pure query helpers for Spendly. No Flask imports. Each function opens
and closes its own get_db() connection."""

from datetime import datetime

from database.db import get_db


def format_currency(amount):
    return f"₹{amount:,.2f}"


# --- Subagent 2 (summary stats + account) adds get_user_by_id() and get_summary_stats() below ---


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    db.close()
    if row is None:
        return None
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {"name": row["name"], "email": row["email"], "member_since": created.strftime("%B %Y")}


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    use_dates = date_from and date_to
    if use_dates:
        total_sql = (
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ?"
        )
        top_sql = (
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ? AND date BETWEEN ? AND ? "
            "GROUP BY category ORDER BY cat_total DESC LIMIT 1"
        )
        params = (user_id, date_from, date_to)
    else:
        total_sql = (
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?"
        )
        top_sql = (
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY cat_total DESC LIMIT 1"
        )
        params = (user_id,)
    total_row = db.execute(total_sql, params).fetchone()
    top_row = db.execute(top_sql, params).fetchone()
    db.close()
    return {
        "total_spent": total_row["total"],
        "transaction_count": total_row["cnt"],
        "top_category": top_row["category"] if top_row else "—",
    }


# --- Subagent 1 (transaction history) adds get_recent_transactions() below ---


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    db = get_db()
    if date_from and date_to:
        sql = (
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? AND date BETWEEN ? AND ? "
            "ORDER BY date DESC, id DESC LIMIT ?"
        )
        params = (user_id, date_from, date_to, limit)
    else:
        sql = (
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?"
        )
        params = (user_id, limit)
    rows = db.execute(sql, params).fetchall()
    db.close()
    return [
        {"date": r["date"], "description": r["description"],
         "category": r["category"], "amount": r["amount"]}
        for r in rows
    ]


# --- Subagent 3 (category breakdown) adds get_category_breakdown() below ---


def get_category_breakdown(user_id, date_from=None, date_to=None):
    db = get_db()
    if date_from and date_to:
        sql = (
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ? AND date BETWEEN ? AND ? "
            "GROUP BY category ORDER BY cat_total DESC"
        )
        params = (user_id, date_from, date_to)
    else:
        sql = (
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY cat_total DESC"
        )
        params = (user_id,)
    rows = db.execute(sql, params).fetchall()
    db.close()
    if not rows:
        return []
    grand_total = sum(r["cat_total"] for r in rows)
    pcts = [round((r["cat_total"] / grand_total) * 100) for r in rows]
    diff = 100 - sum(pcts)
    pcts[0] += diff  # largest category (rows[0], ORDER BY DESC) absorbs rounding remainder
    return [{"name": r["category"], "amount": r["cat_total"], "pct": p} for r, p in zip(rows, pcts)]
