import sqlite3

from flask import Flask, render_template, request, redirect, url_for, abort, session
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"


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

    # Step 4 is UI-only — all data below is hardcoded. Step 5 wires real queries.
    user = {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "initials": "AS",
        "member_since": "March 2024",
    }
    stats = {
        "total_spent": "₹42,180",
        "transaction_count": 27,
        "top_category": "Food",
    }
    transactions = [
        {"date": "12 Jun 2026", "description": "Grocery run — DMart",  "category": "Food",          "amount": "₹2,340"},
        {"date": "10 Jun 2026", "description": "Metro card recharge",  "category": "Transport",     "amount": "₹500"},
        {"date": "08 Jun 2026", "description": "Electricity bill",     "category": "Bills",         "amount": "₹1,820"},
        {"date": "05 Jun 2026", "description": "Pharmacy — Apollo",    "category": "Health",        "amount": "₹640"},
        {"date": "02 Jun 2026", "description": "Movie night — PVR",    "category": "Entertainment", "amount": "₹900"},
    ]
    category_breakdown = [
        {"name": "Food",          "total": "₹14,200", "percent": 34},
        {"name": "Bills",         "total": "₹9,600",  "percent": 23},
        {"name": "Transport",     "total": "₹6,400",  "percent": 15},
        {"name": "Health",        "total": "₹5,180",  "percent": 12},
        {"name": "Entertainment", "total": "₹4,800",  "percent": 11},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


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
    app.run(debug=True, port=5001)
