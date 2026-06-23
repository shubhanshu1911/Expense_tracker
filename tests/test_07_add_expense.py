"""
tests/test_07_add_expense.py

Pytest tests for the Step 07 "Add Expense" feature.

Routes under test:
  GET  /expenses/add  — render the Add Expense form (auth-guarded)
  POST /expenses/add  — validate input, insert row, redirect to /profile (auth-guarded)

Fixture:
  Reuses the project-wide `client` fixture from conftest.py, which:
    - monkeypatches DB_PATH to a fresh temp file per test
    - calls init_db() + seed_db() (seed user: demo@spendly.com / demo123)
    - yields a Flask test client
    - tears down the temp file on exit

Seed user (user_id=1):
  email:    demo@spendly.com
  password: demo123
"""

import sqlite3

import pytest
import database.db as db_module


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

VALID_EXPENSE = {
    "amount": "49.99",
    "category": "Food",
    "date": "2026-06-20",
    "description": "Test lunch",
}

ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
]


def _login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    """Log in with the seed demo account and return the response."""
    return client.post("/login", data={"email": email, "password": password})


def _count_expenses(db_path):
    """Return the total number of rows currently in the expenses table."""
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    return count


def _get_all_expenses(db_path):
    """Return all rows from the expenses table as a list of dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseAuthGuard:
    """Unauthenticated access to /expenses/add must be rejected."""

    def test_get_unauthenticated_redirects_to_login(self, client):
        """GET /expenses/add while logged out must redirect to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            f"Expected 302 redirect for unauthenticated GET, got {response.status_code}"
        )
        assert "/login" in response.headers["Location"], (
            f"Redirect must point to /login, got {response.headers['Location']}"
        )

    def test_post_unauthenticated_redirects_to_login(self, client):
        """POST /expenses/add while logged out must redirect to /login."""
        response = client.post("/expenses/add", data=VALID_EXPENSE)
        assert response.status_code == 302, (
            f"Expected 302 redirect for unauthenticated POST, got {response.status_code}"
        )
        assert "/login" in response.headers["Location"], (
            f"Redirect must point to /login, got {response.headers['Location']}"
        )

    def test_post_unauthenticated_inserts_no_row(self, client, monkeypatch, tmp_path):
        """Unauthenticated POST must not insert any row into the expenses table."""
        # Capture the patched DB path to inspect it directly
        db_path = db_module.DB_PATH
        rows_before = _count_expenses(db_path)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before, (
            "Unauthenticated POST must not insert a row into expenses; "
            f"rows went from {rows_before} to {rows_after}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /expenses/add — form rendering
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseGetForm:
    """GET /expenses/add for a logged-in user must render the full form."""

    def test_get_authenticated_returns_200(self, client):
        """GET /expenses/add while logged in must return 200."""
        _login(client)
        response = client.get("/expenses/add")
        assert response.status_code == 200, (
            f"Expected 200 for authenticated GET /expenses/add, got {response.status_code}"
        )

    def test_get_renders_amount_field(self, client):
        """The form must contain an 'amount' input field."""
        _login(client)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="amount"' in body, (
            "Add Expense form must contain a field with name='amount'"
        )

    def test_get_renders_category_field(self, client):
        """The form must contain a 'category' dropdown or select."""
        _login(client)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="category"' in body, (
            "Add Expense form must contain a field with name='category'"
        )

    def test_get_renders_date_field(self, client):
        """The form must contain a 'date' input field."""
        _login(client)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="date"' in body, (
            "Add Expense form must contain a field with name='date'"
        )

    def test_get_renders_description_field(self, client):
        """The form must contain a 'description' input/textarea field."""
        _login(client)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="description"' in body, (
            "Add Expense form must contain a field with name='description'"
        )

    @pytest.mark.parametrize("category", ALLOWED_CATEGORIES)
    def test_get_renders_all_categories_in_dropdown(self, client, category):
        """The form must render each of the seven allowed categories as an option."""
        _login(client)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert category in body, (
            f"Category '{category}' must appear in the Add Expense form dropdown"
        )

    def test_get_form_extends_base_template(self, client):
        """The rendered page must share base.html landmarks (e.g. a nav or common element)."""
        _login(client)
        body = client.get("/expenses/add").get_data(as_text=True)
        # base.html always provides a DOCTYPE and html root
        assert "<!DOCTYPE html>" in body or "<!doctype html>" in body.lower(), (
            "Response must be a full HTML page extending base.html"
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /expenses/add — happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseHappyPath:
    """Valid POST /expenses/add inserts a row and redirects correctly."""

    def test_valid_post_returns_302(self, client):
        """POST with valid data must return 302 before following the redirect."""
        _login(client)
        response = client.post("/expenses/add", data=VALID_EXPENSE)
        assert response.status_code == 302, (
            f"Expected 302 redirect after valid POST, got {response.status_code}"
        )

    def test_valid_post_redirects_to_profile(self, client):
        """The 302 Location header must point to /profile."""
        _login(client)
        response = client.post("/expenses/add", data=VALID_EXPENSE)
        assert "/profile" in response.headers["Location"], (
            f"Expected redirect to /profile, got Location={response.headers['Location']}"
        )

    def test_valid_post_profile_page_returns_200(self, client):
        """Following the redirect after a valid POST must yield a 200 on /profile."""
        _login(client)
        response = client.post(
            "/expenses/add", data=VALID_EXPENSE, follow_redirects=True
        )
        assert response.status_code == 200, (
            f"Expected 200 on /profile after redirect, got {response.status_code}"
        )

    def test_valid_post_inserts_one_row_into_expenses(self, client):
        """A valid POST must insert exactly one new row into the expenses table."""
        db_path = db_module.DB_PATH
        rows_before = _count_expenses(db_path)
        _login(client)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before + 1, (
            f"Expected exactly 1 new expense row; before={rows_before}, after={rows_after}"
        )

    def test_valid_post_row_has_correct_amount(self, client):
        """The inserted row must store the submitted amount as a float."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows = _get_all_expenses(db_path)
        newest = rows[0]
        assert newest["amount"] == pytest.approx(49.99), (
            f"Expected amount=49.99, got {newest['amount']}"
        )

    def test_valid_post_row_has_correct_category(self, client):
        """The inserted row must store the submitted category exactly."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows = _get_all_expenses(db_path)
        newest = rows[0]
        assert newest["category"] == "Food", (
            f"Expected category='Food', got '{newest['category']}'"
        )

    def test_valid_post_row_has_correct_date(self, client):
        """The inserted row must store the submitted date in YYYY-MM-DD format."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows = _get_all_expenses(db_path)
        newest = rows[0]
        assert newest["date"] == "2026-06-20", (
            f"Expected date='2026-06-20', got '{newest['date']}'"
        )

    def test_valid_post_row_has_correct_description(self, client):
        """The inserted row must store the submitted description."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows = _get_all_expenses(db_path)
        newest = rows[0]
        assert newest["description"] == "Test lunch", (
            f"Expected description='Test lunch', got '{newest['description']}'"
        )

    def test_valid_post_row_has_correct_user_id(self, client):
        """The inserted row must be associated with the logged-in user's id."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post("/expenses/add", data=VALID_EXPENSE)
        rows = _get_all_expenses(db_path)
        newest = rows[0]
        # The seed demo user is always user_id=1 from seed_db()
        assert newest["user_id"] == 1, (
            f"Expected user_id=1 for the seed demo user, got {newest['user_id']}"
        )

    def test_valid_post_success_flash_appears_on_profile(self, client):
        """A success flash message must appear on /profile after a valid submission."""
        _login(client)
        response = client.post(
            "/expenses/add", data=VALID_EXPENSE, follow_redirects=True
        )
        body = response.get_data(as_text=True)
        # The spec says flash a confirmation message; the implementation uses "Expense added successfully."
        assert "Expense added" in body or "successfully" in body, (
            "A success flash message must appear on the profile page after adding an expense"
        )

    def test_valid_post_expense_visible_on_profile(self, client):
        """After adding an expense, the description must appear in the transaction list."""
        _login(client)
        expense = dict(VALID_EXPENSE)
        expense["description"] = "UniqueDescriptionXYZ"
        client.post("/expenses/add", data=expense, follow_redirects=True)
        # Re-visit profile to check the transaction list
        response = client.get("/profile")
        body = response.get_data(as_text=True)
        assert "UniqueDescriptionXYZ" in body, (
            "The newly added expense description must be visible on /profile"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Optional description — blank stored as NULL
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseOptionalDescription:
    """Description is optional; blank value must be accepted and stored as NULL."""

    def test_blank_description_is_accepted(self, client):
        """POST with an empty description string must succeed (no validation error)."""
        _login(client)
        data = dict(VALID_EXPENSE, description="")
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            f"Blank description must not cause a validation error; expected 302, got {response.status_code}"
        )

    def test_blank_description_inserts_row(self, client):
        """POST with blank description must still insert a row into expenses."""
        db_path = db_module.DB_PATH
        rows_before = _count_expenses(db_path)
        _login(client)
        client.post("/expenses/add", data=dict(VALID_EXPENSE, description=""))
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before + 1, (
            f"Blank description must not prevent row insertion; before={rows_before}, after={rows_after}"
        )

    def test_blank_description_stored_as_null_or_empty(self, client):
        """Blank description must be stored as NULL (or empty string) in the DB."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post("/expenses/add", data=dict(VALID_EXPENSE, description=""))
        rows = _get_all_expenses(db_path)
        newest = rows[0]
        # Spec says store None; implementation converts "" to None
        assert newest["description"] is None or newest["description"] == "", (
            f"Blank description must be stored as NULL or empty string, got '{newest['description']}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — amount
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseAmountValidation:
    """Amount validation: must be a positive number, present and numeric."""

    @pytest.mark.parametrize("bad_amount,label", [
        ("", "missing (empty string)"),
        ("abc", "non-numeric string"),
        ("12.3.4", "multiple decimals"),
        ("$50", "amount with currency symbol"),
    ])
    def test_non_numeric_amount_rerenders_form(self, client, bad_amount, label):
        """Non-numeric or missing amount must re-render the form, not redirect."""
        _login(client)
        data = dict(VALID_EXPENSE, amount=bad_amount)
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            f"Non-numeric amount ({label}) must re-render form (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("", "missing (empty string)"),
        ("abc", "non-numeric string"),
        ("12.3.4", "multiple decimals"),
        ("$50", "amount with currency symbol"),
    ])
    def test_non_numeric_amount_shows_error_message(self, client, bad_amount, label):
        """Non-numeric or missing amount must include an error in the response body."""
        _login(client)
        data = dict(VALID_EXPENSE, amount=bad_amount)
        response = client.post("/expenses/add", data=data)
        body = response.get_data(as_text=True)
        assert "error" in body.lower() or "valid" in body.lower() or "number" in body.lower(), (
            f"Non-numeric amount ({label}) must produce a visible error; body snippet: {body[:300]}"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("", "missing (empty string)"),
        ("abc", "non-numeric string"),
    ])
    def test_non_numeric_amount_inserts_no_row(self, client, bad_amount, label):
        """Non-numeric amount must not insert any row into expenses."""
        db_path = db_module.DB_PATH
        _login(client)
        rows_before = _count_expenses(db_path)
        client.post("/expenses/add", data=dict(VALID_EXPENSE, amount=bad_amount))
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before, (
            f"Non-numeric amount ({label}) must not insert a row; before={rows_before}, after={rows_after}"
        )

    @pytest.mark.parametrize("zero_or_negative,label", [
        ("0", "zero"),
        ("0.00", "zero as float string"),
        ("-1", "negative integer"),
        ("-0.01", "small negative float"),
        ("-100", "negative large value"),
    ])
    def test_zero_or_negative_amount_rerenders_form(self, client, zero_or_negative, label):
        """Zero or negative amount must re-render the form."""
        _login(client)
        data = dict(VALID_EXPENSE, amount=zero_or_negative)
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            f"Amount {label} must re-render form (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("zero_or_negative,label", [
        ("0", "zero"),
        ("-1", "negative integer"),
        ("-0.01", "small negative float"),
    ])
    def test_zero_or_negative_amount_inserts_no_row(self, client, zero_or_negative, label):
        """Zero or negative amount must not insert any row into expenses."""
        db_path = db_module.DB_PATH
        _login(client)
        rows_before = _count_expenses(db_path)
        client.post("/expenses/add", data=dict(VALID_EXPENSE, amount=zero_or_negative))
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before, (
            f"Amount {label} must not insert a row; before={rows_before}, after={rows_after}"
        )

    @pytest.mark.parametrize("zero_or_negative", ["0", "-1", "-0.01"])
    def test_zero_or_negative_amount_shows_error(self, client, zero_or_negative):
        """Zero or negative amount must show an appropriate error message."""
        _login(client)
        data = dict(VALID_EXPENSE, amount=zero_or_negative)
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "zero" in body.lower() or "positive" in body.lower() or "greater" in body.lower() or "error" in body.lower(), (
            f"Amount {zero_or_negative!r} must produce a visible 'greater than zero' error"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — category
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseCategoryValidation:
    """Category validation: must be one of the seven allowed values."""

    @pytest.mark.parametrize("bad_category", [
        "Clothing",           # plausible but not in the list
        "food",               # wrong case
        "FOOD",               # all caps
        "Entertainment ",     # trailing space
        "",                   # blank
        "<script>alert(1)</script>",  # XSS attempt
        "'; DROP TABLE expenses;--",  # SQL injection attempt (parameterized queries safe)
    ])
    def test_invalid_category_rerenders_form(self, client, bad_category):
        """An invalid category must re-render the form, not redirect."""
        _login(client)
        data = dict(VALID_EXPENSE, category=bad_category)
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            f"Invalid category {bad_category!r} must re-render form (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_category", [
        "Clothing",
        "food",
        "",
    ])
    def test_invalid_category_shows_error(self, client, bad_category):
        """An invalid category must include a visible error message."""
        _login(client)
        data = dict(VALID_EXPENSE, category=bad_category)
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "error" in body.lower() or "valid" in body.lower() or "category" in body.lower(), (
            f"Invalid category {bad_category!r} must produce a visible error"
        )

    @pytest.mark.parametrize("bad_category", [
        "Clothing",
        "food",
        "",
        "'; DROP TABLE expenses;--",
    ])
    def test_invalid_category_inserts_no_row(self, client, bad_category):
        """An invalid category must not insert any row into expenses."""
        db_path = db_module.DB_PATH
        _login(client)
        rows_before = _count_expenses(db_path)
        client.post("/expenses/add", data=dict(VALID_EXPENSE, category=bad_category))
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before, (
            f"Invalid category {bad_category!r} must not insert a row; before={rows_before}, after={rows_after}"
        )

    @pytest.mark.parametrize("valid_category", ALLOWED_CATEGORIES)
    def test_each_allowed_category_is_accepted(self, client, valid_category):
        """Every one of the seven allowed categories must be accepted and result in a 302."""
        _login(client)
        data = dict(VALID_EXPENSE, category=valid_category)
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            f"Valid category '{valid_category}' should redirect (302), got {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — date
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseDateValidation:
    """Date validation: must be present and a real date in YYYY-MM-DD format."""

    @pytest.mark.parametrize("bad_date,label", [
        ("", "missing/empty"),
        ("not-a-date", "arbitrary string"),
        ("20-06-2026", "DD-MM-YYYY format"),
        ("06/20/2026", "MM/DD/YYYY format"),
        ("2026-13-01", "month 13 out of range"),
        ("2026-02-30", "Feb 30 does not exist"),
        ("2026-00-10", "month 0 out of range"),
        ("2026-06-00", "day 0 out of range"),
    ])
    def test_invalid_date_rerenders_form(self, client, bad_date, label):
        """A missing or malformed date must re-render the form, not redirect."""
        _login(client)
        data = dict(VALID_EXPENSE, date=bad_date)
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200, (
            f"Invalid date ({label}: {bad_date!r}) must re-render form (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_date,label", [
        ("", "missing/empty"),
        ("not-a-date", "arbitrary string"),
        ("2026-02-30", "Feb 30 does not exist"),
    ])
    def test_invalid_date_shows_error(self, client, bad_date, label):
        """A missing or malformed date must include a visible error message."""
        _login(client)
        data = dict(VALID_EXPENSE, date=bad_date)
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "error" in body.lower() or "valid" in body.lower() or "date" in body.lower(), (
            f"Invalid date ({label}) must produce a visible error; body snippet: {body[:300]}"
        )

    @pytest.mark.parametrize("bad_date,label", [
        ("", "missing/empty"),
        ("not-a-date", "arbitrary string"),
        ("2026-02-30", "Feb 30 does not exist"),
        ("2026-13-01", "month 13 out of range"),
    ])
    def test_invalid_date_inserts_no_row(self, client, bad_date, label):
        """A missing or malformed date must not insert any row into expenses."""
        db_path = db_module.DB_PATH
        _login(client)
        rows_before = _count_expenses(db_path)
        client.post("/expenses/add", data=dict(VALID_EXPENSE, date=bad_date))
        rows_after = _count_expenses(db_path)
        assert rows_after == rows_before, (
            f"Invalid date ({label}: {bad_date!r}) must not insert a row; before={rows_before}, after={rows_after}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Input preservation on validation failure
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseInputPreservation:
    """On validation failure the form must be re-rendered with the submitted values present."""

    def test_submitted_amount_preserved_on_invalid_category(self, client):
        """When category is invalid, the submitted amount should appear in the re-rendered form."""
        _login(client)
        data = dict(VALID_EXPENSE, category="BadCategory", amount="123.45")
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "123.45" in body, (
            "Submitted amount '123.45' must appear in re-rendered form when category validation fails"
        )

    def test_submitted_category_preserved_on_invalid_amount(self, client):
        """When amount is invalid, the submitted category should appear in the re-rendered form."""
        _login(client)
        data = dict(VALID_EXPENSE, amount="abc", category="Transport")
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "Transport" in body, (
            "Submitted category 'Transport' must appear in re-rendered form when amount validation fails"
        )

    def test_submitted_date_preserved_on_invalid_amount(self, client):
        """When amount is invalid, the submitted date should appear in the re-rendered form."""
        _login(client)
        data = dict(VALID_EXPENSE, amount="abc", date="2026-06-15")
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "2026-06-15" in body, (
            "Submitted date '2026-06-15' must appear in re-rendered form when amount validation fails"
        )

    def test_submitted_description_preserved_on_invalid_date(self, client):
        """When date is invalid, the submitted description should appear in the re-rendered form."""
        _login(client)
        data = dict(VALID_EXPENSE, date="bad-date", description="My unique description")
        body = client.post("/expenses/add", data=data).get_data(as_text=True)
        assert "My unique description" in body, (
            "Submitted description must appear in re-rendered form when date validation fails"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Multi-user isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseUserIsolation:
    """Expenses submitted by one user must not appear under another user's profile."""

    def test_expense_linked_to_submitting_user_not_other(self, client):
        """A second user's expense must carry their own user_id, not the first user's."""
        from database.db import create_user

        # Register a second user
        client.post(
            "/register",
            data={
                "name": "Second User",
                "email": "second@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        # Log in as second user and add an expense
        client.post("/login", data={"email": "second@example.com", "password": "password123"})
        client.post(
            "/expenses/add",
            data={
                "amount": "77.77",
                "category": "Health",
                "date": "2026-06-21",
                "description": "SecondUserExpense",
            },
        )
        # Find the new row
        db_path = db_module.DB_PATH
        rows = _get_all_expenses(db_path)
        second_user_rows = [r for r in rows if r["description"] == "SecondUserExpense"]
        assert len(second_user_rows) == 1, (
            "Exactly one row with description='SecondUserExpense' must be in the DB"
        )
        assert second_user_rows[0]["user_id"] != 1, (
            "The second user's expense must NOT carry user_id=1 (the demo/seed user)"
        )
