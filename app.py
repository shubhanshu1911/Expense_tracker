import os
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, flash, render_template, request, redirect, url_for, abort, session
from werkzeug.security import check_password_hash

from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    insert_expense,
)
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    format_currency,
)

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"

EXPENSE_CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
]

MAX_EXPENSE_AMOUNT = 1_000_000
MAX_DESCRIPTION_LENGTH = 300


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _build_presets(today):
    return {
        "this_month":    (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": ((today - timedelta(days=90)).isoformat(), today.isoformat()),
        "last_6_months": ((today - timedelta(days=180)).isoformat(), today.isoformat()),
    }


def _detect_active_preset(presets, date_from_str, date_to_str):
    if not (date_from_str and date_to_str):
        return None
    for name, (f, t) in presets.items():
        if date_from_str == f and date_to_str == t:
            return name
    return None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        return render_template("register.html", error="All fields are required.")

    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered.")

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="All fields are required.")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # --- Date filter ---
    date_from = _parse_date(request.args.get("date_from", ""))
    date_to = _parse_date(request.args.get("date_to", ""))
    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None
    date_from_str = date_from.isoformat() if date_from else None
    date_to_str = date_to.isoformat() if date_to else None
    presets = _build_presets(date.today())
    active_preset = _detect_active_preset(presets, date_from_str, date_to_str)

    # --- [SUBAGENT 2: summary stats + account] ---
    db_user = get_user_by_id(user_id)
    user = {
        "name": db_user["name"],
        "email": db_user["email"],
        "initials": "".join(p[0].upper() for p in db_user["name"].split()[:2]),
        "member_since": db_user["member_since"],
    }
    raw_stats = get_summary_stats(user_id, date_from=date_from_str, date_to=date_to_str)
    stats = {
        "total_spent": format_currency(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category": raw_stats["top_category"],
    }
    # --- [END SUBAGENT 2] ---

    # --- [SUBAGENT 1: transaction history] ---
    raw_transactions = get_recent_transactions(user_id, date_from=date_from_str, date_to=date_to_str)
    transactions = [
        {
            "date": tx["date"],
            "description": tx["description"],
            "category": tx["category"],
            "amount": format_currency(tx["amount"]),
        }
        for tx in raw_transactions
    ]
    # --- [END SUBAGENT 1] ---

    # --- [SUBAGENT 3: category breakdown] ---
    raw_breakdown = get_category_breakdown(user_id, date_from=date_from_str, date_to=date_to_str)
    category_breakdown = [
        {
            "name": cat["name"],
            "total": format_currency(cat["amount"]),
            "percent": cat["pct"],
        }
        for cat in raw_breakdown
    ]
    # --- [END SUBAGENT 3] ---

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
        date_from_str=date_from_str,
        date_to_str=date_to_str,
        presets=presets,
        active_preset=active_preset,
    )


def _render_add_expense_form(form, error=None):
    return render_template(
        "add_expense.html",
        categories=EXPENSE_CATEGORIES,
        today=date.today().isoformat(),
        form=form,
        error=error,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return _render_add_expense_form(form={})

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "")
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description,
    }

    try:
        amount = float(amount_raw)
    except ValueError:
        return _render_add_expense_form(form, "Amount must be a valid number.")
    if amount <= 0:
        return _render_add_expense_form(form, "Amount must be greater than zero.")
    if amount > MAX_EXPENSE_AMOUNT:
        return _render_add_expense_form(
            form, f"Amount must not exceed {MAX_EXPENSE_AMOUNT:,}."
        )

    if category not in EXPENSE_CATEGORIES:
        return _render_add_expense_form(form, "Please select a valid category.")

    parsed = _parse_date(date_raw)
    if parsed is None:
        return _render_add_expense_form(
            form, "Please enter a valid date (YYYY-MM-DD)."
        )

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return _render_add_expense_form(
            form,
            f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.",
        )

    desc_value = description or None

    insert_expense(
        session["user_id"], amount, category, parsed.isoformat(), desc_value
    )
    flash("Expense added successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
