"""
tests/test_08_edit_expense.py

Pytest tests for the Step 08 "Edit Expense" feature.

Routes under test:
  GET  /expenses/<id>/edit  — render the Edit Expense form pre-filled with
                               current values (auth-guarded, ownership-scoped)
  POST /expenses/<id>/edit  — validate input, update row, redirect to /profile
                               (auth-guarded, ownership-scoped)

Fixture:
  Reuses the project-wide `client` fixture from conftest.py, which:
    - monkeypatches DB_PATH to a fresh temp file per test
    - calls init_db() + seed_db() (seed user: demo@spendly.com / demo123)
    - yields a Flask test client
    - tears down the temp file on exit

Seed user (user_id=1):
  name:     Demo User
  email:    demo@spendly.com
  password: demo123
  expenses: ids 1-8

Expense id=1 seed row:
  amount=850.00, category='Food', date='2026-06-01', description='Groceries'
"""

import sqlite3

import pytest
import database.db as db_module


# ─────────────────────────────────────────────────────────────────────────────
# Constants & helpers
# ─────────────────────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

# A seeded expense we will edit (belongs to user_id=1)
EDIT_TARGET_ID = 1  # amount=850, category='Food', date='2026-06-01', desc='Groceries'

VALID_EDIT = {
    "amount": "123.45",
    "category": "Transport",
    "date": "2026-07-15",
    "description": "Updated commute cost",
}

ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
]

MAX_EXPENSE_AMOUNT = 1_000_000
MAX_DESCRIPTION_LENGTH = 300


def _login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    """Log in with the seed demo account and return the response."""
    return client.post("/login", data={"email": email, "password": password})


def _get_expense_row(db_path, expense_id):
    """Fetch a single expense row from the DB by id. Returns a dict or None."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _create_second_user_with_expense(db_path):
    """
    Insert a second user and one expense owned by that user directly into the DB.
    Returns (user2_id, expense2_id).
    """
    from werkzeug.security import generate_password_hash
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@spendly.com", generate_password_hash("otherpass")),
    )
    conn.commit()
    user2_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user2_id, 99.00, "Other", "2026-06-20", "Other user's expense"),
    )
    conn.commit()
    expense2_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return user2_id, expense2_id


def _edit_url(expense_id):
    return f"/expenses/{expense_id}/edit"


# ─────────────────────────────────────────────────────────────────────────────
# Auth guard tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseAuthGuard:
    """Unauthenticated access to /expenses/<id>/edit must be rejected."""

    def test_get_unauthenticated_redirects_to_login(self, client):
        """GET /expenses/<id>/edit while logged out must return 302 to /login."""
        response = client.get(_edit_url(EDIT_TARGET_ID))
        assert response.status_code == 302, (
            f"Expected 302 for unauthenticated GET, got {response.status_code}"
        )
        assert "/login" in response.headers["Location"], (
            f"Redirect must point to /login, got {response.headers['Location']}"
        )

    def test_post_unauthenticated_redirects_to_login(self, client):
        """POST /expenses/<id>/edit while logged out must return 302 to /login."""
        response = client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        assert response.status_code == 302, (
            f"Expected 302 for unauthenticated POST, got {response.status_code}"
        )
        assert "/login" in response.headers["Location"], (
            f"Redirect must point to /login, got {response.headers['Location']}"
        )

    def test_post_unauthenticated_does_not_modify_row(self, client):
        """Unauthenticated POST must not change the expense row in the DB."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["amount"] == row_after["amount"], (
            "Unauthenticated POST must not change the amount of the target expense"
        )
        assert row_before["category"] == row_after["category"], (
            "Unauthenticated POST must not change the category of the target expense"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /expenses/<id>/edit — form rendering and pre-fill
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseGetForm:
    """GET /expenses/<id>/edit for a logged-in owner must return a pre-filled form."""

    def test_get_authenticated_returns_200(self, client):
        """Authenticated GET for an owned expense must return 200."""
        _login(client)
        response = client.get(_edit_url(EDIT_TARGET_ID))
        assert response.status_code == 200, (
            f"Expected 200 for authenticated GET /expenses/{EDIT_TARGET_ID}/edit, "
            f"got {response.status_code}"
        )

    def test_get_renders_amount_field(self, client):
        """The edit form must contain an 'amount' input field."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        assert 'name="amount"' in body, (
            "Edit Expense form must contain a field with name='amount'"
        )

    def test_get_renders_category_field(self, client):
        """The edit form must contain a 'category' dropdown."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        assert 'name="category"' in body, (
            "Edit Expense form must contain a field with name='category'"
        )

    def test_get_renders_date_field(self, client):
        """The edit form must contain a 'date' input field."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        assert 'name="date"' in body, (
            "Edit Expense form must contain a field with name='date'"
        )

    def test_get_renders_description_field(self, client):
        """The edit form must contain a 'description' input/textarea field."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        assert 'name="description"' in body, (
            "Edit Expense form must contain a field with name='description'"
        )

    def test_get_prefills_amount(self, client):
        """The form must be pre-filled with the expense's current amount."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        # Seed expense id=1 has amount=850.0; accept '850' or '850.0' or '850.00'
        assert "850" in body, (
            "Edit form must pre-fill the amount field with the existing value (850)"
        )

    def test_get_prefills_category(self, client):
        """The form must pre-select the expense's current category."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        # Seed expense id=1 has category='Food'
        assert "Food" in body, (
            "Edit form must pre-fill the category with the existing value ('Food')"
        )

    def test_get_prefills_date(self, client):
        """The form must pre-fill the expense's current date."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        # Seed expense id=1 has date='2026-06-01'
        assert "2026-06-01" in body, (
            "Edit form must pre-fill the date with the existing value ('2026-06-01')"
        )

    def test_get_prefills_description(self, client):
        """The form must pre-fill the expense's current description."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        # Seed expense id=1 has description='Groceries'
        assert "Groceries" in body, (
            "Edit form must pre-fill the description with the existing value ('Groceries')"
        )

    @pytest.mark.parametrize("category", ALLOWED_CATEGORIES)
    def test_get_renders_all_allowed_categories(self, client, category):
        """All seven allowed categories must appear in the form dropdown."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        assert category in body, (
            f"Category '{category}' must appear in the Edit Expense form dropdown"
        )

    def test_get_extends_base_template(self, client):
        """The rendered page must be a full HTML page extending base.html."""
        _login(client)
        body = client.get(_edit_url(EDIT_TARGET_ID)).get_data(as_text=True)
        assert "<!DOCTYPE html>" in body or "<!doctype html>" in body.lower(), (
            "Edit Expense response must be a full HTML page (DOCTYPE present)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Profile page — Edit link per transaction row
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseProfileLink:
    """The profile transaction table must expose an Edit link for each expense."""

    def test_profile_contains_edit_link_for_seeded_expense(self, client):
        """The /profile page must contain a link to the edit form for at least one seeded expense."""
        _login(client)
        body = client.get("/profile").get_data(as_text=True)
        # Any of the 8 seeded expense ids (1-8) must have an edit href
        found = any(f"/expenses/{eid}/edit" in body for eid in range(1, 9))
        assert found, (
            "Profile page must contain at least one /expenses/<id>/edit href link "
            "in the transaction table"
        )

    def test_profile_edit_link_points_to_correct_expense(self, client):
        """The Edit link for expense id=1 must point to /expenses/1/edit."""
        _login(client)
        body = client.get("/profile").get_data(as_text=True)
        assert "/expenses/1/edit" in body, (
            "Profile page must contain a link to /expenses/1/edit for the first seeded expense"
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /expenses/<id>/edit — happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseHappyPath:
    """Valid POST /expenses/<id>/edit updates the DB row and redirects to /profile."""

    def test_valid_post_returns_302(self, client):
        """A valid POST must return 302 before following the redirect."""
        _login(client)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        assert response.status_code == 302, (
            f"Expected 302 after valid POST to edit expense, got {response.status_code}"
        )

    def test_valid_post_redirects_to_profile(self, client):
        """The 302 Location header must point to /profile."""
        _login(client)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        assert "/profile" in response.headers["Location"], (
            f"Expected redirect to /profile, got Location={response.headers['Location']}"
        )

    def test_valid_post_profile_returns_200_after_redirect(self, client):
        """Following the redirect after a valid edit POST must yield 200."""
        _login(client)
        response = client.post(
            _edit_url(EDIT_TARGET_ID), data=VALID_EDIT, follow_redirects=True
        )
        assert response.status_code == 200, (
            f"Expected 200 on /profile after redirect, got {response.status_code}"
        )

    def test_valid_post_updates_amount_in_db(self, client):
        """A valid POST must persist the new amount in the expenses table."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        row = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row["amount"] == pytest.approx(123.45), (
            f"Expected updated amount=123.45 in DB, got {row['amount']}"
        )

    def test_valid_post_updates_category_in_db(self, client):
        """A valid POST must persist the new category in the expenses table."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        row = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row["category"] == "Transport", (
            f"Expected updated category='Transport' in DB, got '{row['category']}'"
        )

    def test_valid_post_updates_date_in_db(self, client):
        """A valid POST must persist the new date in the expenses table."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        row = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row["date"] == "2026-07-15", (
            f"Expected updated date='2026-07-15' in DB, got '{row['date']}'"
        )

    def test_valid_post_updates_description_in_db(self, client):
        """A valid POST must persist the new description in the expenses table."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        row = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row["description"] == "Updated commute cost", (
            f"Expected updated description='Updated commute cost', got '{row['description']}'"
        )

    def test_valid_post_does_not_create_new_row(self, client):
        """A valid edit POST must update the existing row, not insert a new one."""
        db_path = db_module.DB_PATH
        conn = sqlite3.connect(db_path)
        count_before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        conn = sqlite3.connect(db_path)
        count_after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert count_after == count_before, (
            f"Edit POST must not insert a new row; expense count changed from "
            f"{count_before} to {count_after}"
        )

    def test_valid_post_preserves_user_id(self, client):
        """A valid edit POST must not change the user_id of the expense row."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT)
        row = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row["user_id"] == 1, (
            f"Edit must not alter the user_id; expected 1, got {row['user_id']}"
        )

    def test_valid_post_flash_message_appears_on_profile(self, client):
        """A success flash message must appear on /profile after a valid edit."""
        _login(client)
        response = client.post(
            _edit_url(EDIT_TARGET_ID), data=VALID_EDIT, follow_redirects=True
        )
        body = response.get_data(as_text=True)
        assert "updated" in body.lower() or "successfully" in body.lower(), (
            "A flash confirmation containing 'updated' or 'successfully' must appear "
            "on the profile page after a successful edit"
        )

    def test_valid_post_updated_amount_visible_on_profile(self, client):
        """After editing, the new amount must appear in the profile transaction list."""
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=VALID_EDIT, follow_redirects=True)
        body = client.get("/profile").get_data(as_text=True)
        # 123.45 formatted as currency; accept '123' as a substring of '123.45'
        assert "123" in body, (
            "The updated amount (123.45) must be visible on /profile after editing"
        )

    def test_valid_post_updated_description_visible_on_profile(self, client):
        """After editing, the new description must appear in the profile transaction list."""
        _login(client)
        edit_data = dict(VALID_EDIT, description="UniqueEditedDescription")
        client.post(_edit_url(EDIT_TARGET_ID), data=edit_data, follow_redirects=True)
        body = client.get("/profile").get_data(as_text=True)
        assert "UniqueEditedDescription" in body, (
            "The updated description must be visible on /profile after editing"
        )

    @pytest.mark.parametrize("valid_category", ALLOWED_CATEGORIES)
    def test_each_allowed_category_is_accepted(self, client, valid_category):
        """Each of the seven allowed categories must be accepted by a valid POST."""
        _login(client)
        data = dict(VALID_EDIT, category=valid_category)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 302, (
            f"Valid category '{valid_category}' must produce 302 redirect, "
            f"got {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Ownership / 404 security tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseOwnership:
    """Ownership is enforced: users may only edit their own expenses."""

    def test_get_nonexistent_expense_returns_404(self, client):
        """GET for an expense id that does not exist must return 404."""
        _login(client)
        response = client.get(_edit_url(99999))
        assert response.status_code == 404, (
            f"Expected 404 for a non-existent expense id, got {response.status_code}"
        )

    def test_post_nonexistent_expense_returns_404(self, client):
        """POST for an expense id that does not exist must return 404."""
        _login(client)
        response = client.post(_edit_url(99999), data=VALID_EDIT)
        assert response.status_code == 404, (
            f"Expected 404 for POST to a non-existent expense id, got {response.status_code}"
        )

    def test_get_another_users_expense_returns_404(self, client):
        """GET for an expense owned by another user must return 404 (no data leak)."""
        db_path = db_module.DB_PATH
        _, expense2_id = _create_second_user_with_expense(db_path)
        _login(client)  # log in as seed demo user (user_id=1)
        response = client.get(_edit_url(expense2_id))
        assert response.status_code == 404, (
            f"Expected 404 when accessing another user's expense on GET, "
            f"got {response.status_code}"
        )

    def test_post_another_users_expense_returns_404(self, client):
        """POST to an expense owned by another user must return 404."""
        db_path = db_module.DB_PATH
        _, expense2_id = _create_second_user_with_expense(db_path)
        _login(client)  # log in as seed demo user (user_id=1)
        response = client.post(_edit_url(expense2_id), data=VALID_EDIT)
        assert response.status_code == 404, (
            f"Expected 404 when POSTing to another user's expense, "
            f"got {response.status_code}"
        )

    def test_post_another_users_expense_does_not_modify_row(self, client):
        """POST to another user's expense must leave the row unchanged in the DB."""
        db_path = db_module.DB_PATH
        _, expense2_id = _create_second_user_with_expense(db_path)
        row_before = _get_expense_row(db_path, expense2_id)
        _login(client)
        client.post(_edit_url(expense2_id), data=VALID_EDIT)
        row_after = _get_expense_row(db_path, expense2_id)
        assert row_before["amount"] == row_after["amount"], (
            "Rejected cross-user POST must not alter the other user's expense amount"
        )
        assert row_before["description"] == row_after["description"], (
            "Rejected cross-user POST must not alter the other user's expense description"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — amount
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseAmountValidation:
    """Amount validation mirrors the add-expense rules exactly."""

    @pytest.mark.parametrize("bad_amount,label", [
        ("", "empty string"),
        ("abc", "non-numeric string"),
        ("12.3.4", "multiple decimals"),
        ("$50", "currency symbol"),
    ])
    def test_non_numeric_amount_rerenders_form(self, client, bad_amount, label):
        """Non-numeric or missing amount must re-render the edit form (200)."""
        _login(client)
        data = dict(VALID_EDIT, amount=bad_amount)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 200, (
            f"Non-numeric amount ({label}: {bad_amount!r}) must re-render form (200), "
            f"got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("", "empty string"),
        ("abc", "non-numeric string"),
    ])
    def test_non_numeric_amount_shows_error(self, client, bad_amount, label):
        """Non-numeric amount must include a visible error in the response."""
        _login(client)
        data = dict(VALID_EDIT, amount=bad_amount)
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "valid" in body.lower()
            or "number" in body.lower()
        ), (
            f"Non-numeric amount ({label}) must produce a visible error"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("", "empty string"),
        ("abc", "non-numeric string"),
    ])
    def test_non_numeric_amount_does_not_modify_row(self, client, bad_amount, label):
        """Non-numeric amount must leave the expense row unchanged."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=dict(VALID_EDIT, amount=bad_amount))
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["amount"] == row_after["amount"], (
            f"Non-numeric amount ({label}) must not modify the DB row"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("0", "zero"),
        ("0.00", "zero float"),
        ("-1", "negative integer"),
        ("-0.01", "small negative float"),
        ("-999", "large negative"),
    ])
    def test_zero_or_negative_amount_rerenders_form(self, client, bad_amount, label):
        """Zero or negative amount must re-render the edit form (200)."""
        _login(client)
        data = dict(VALID_EDIT, amount=bad_amount)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 200, (
            f"Amount {label} ({bad_amount!r}) must re-render form (200), "
            f"got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_amount", ["0", "-1", "-0.01"])
    def test_zero_or_negative_amount_shows_error(self, client, bad_amount):
        """Zero or negative amount must show a suitable error message."""
        _login(client)
        body = client.post(
            _edit_url(EDIT_TARGET_ID), data=dict(VALID_EDIT, amount=bad_amount)
        ).get_data(as_text=True)
        assert (
            "zero" in body.lower()
            or "positive" in body.lower()
            or "greater" in body.lower()
            or "error" in body.lower()
        ), (
            f"Amount {bad_amount!r} must produce a visible 'greater than zero' error"
        )

    @pytest.mark.parametrize("bad_amount", ["0", "-1"])
    def test_zero_or_negative_amount_does_not_modify_row(self, client, bad_amount):
        """Zero or negative amount must leave the expense row unchanged."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=dict(VALID_EDIT, amount=bad_amount))
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["amount"] == row_after["amount"], (
            f"Amount {bad_amount!r} must not modify the DB row"
        )

    def test_amount_above_max_rerenders_form(self, client):
        """Amount exceeding MAX_EXPENSE_AMOUNT (1,000,000) must re-render the form."""
        _login(client)
        data = dict(VALID_EDIT, amount=str(MAX_EXPENSE_AMOUNT + 1))
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 200, (
            f"Amount above MAX_EXPENSE_AMOUNT must re-render form (200), "
            f"got {response.status_code}"
        )

    def test_amount_above_max_shows_error(self, client):
        """Amount exceeding MAX_EXPENSE_AMOUNT must include a visible error."""
        _login(client)
        data = dict(VALID_EDIT, amount=str(MAX_EXPENSE_AMOUNT + 1))
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "exceed" in body.lower()
            or "maximum" in body.lower()
            or "max" in body.lower()
        ), (
            "Amount above MAX_EXPENSE_AMOUNT must produce a visible error message"
        )

    def test_amount_above_max_does_not_modify_row(self, client):
        """Amount exceeding MAX_EXPENSE_AMOUNT must leave the expense row unchanged."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        _login(client)
        client.post(
            _edit_url(EDIT_TARGET_ID),
            data=dict(VALID_EDIT, amount=str(MAX_EXPENSE_AMOUNT + 1)),
        )
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["amount"] == row_after["amount"], (
            "Amount above MAX_EXPENSE_AMOUNT must not modify the DB row"
        )

    def test_amount_exactly_at_max_is_accepted(self, client):
        """Amount exactly equal to MAX_EXPENSE_AMOUNT (1,000,000) must be accepted."""
        _login(client)
        data = dict(VALID_EDIT, amount=str(MAX_EXPENSE_AMOUNT))
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 302, (
            f"Amount exactly at MAX_EXPENSE_AMOUNT must be accepted (302), "
            f"got {response.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — category
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseCategoryValidation:
    """Category must be one of the seven allowed values."""

    @pytest.mark.parametrize("bad_category", [
        "Clothing",
        "food",                           # wrong case
        "FOOD",                           # all-caps
        "Transport ",                     # trailing space
        "",                               # blank
        "<script>alert(1)</script>",      # XSS attempt
        "'; DROP TABLE expenses;--",      # SQL injection (parameterised queries handle it)
    ])
    def test_invalid_category_rerenders_form(self, client, bad_category):
        """An invalid category must re-render the edit form (200), not redirect."""
        _login(client)
        data = dict(VALID_EDIT, category=bad_category)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 200, (
            f"Invalid category {bad_category!r} must re-render form (200), "
            f"got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_category", ["Clothing", "food", ""])
    def test_invalid_category_shows_error(self, client, bad_category):
        """An invalid category must show a visible error message."""
        _login(client)
        data = dict(VALID_EDIT, category=bad_category)
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "valid" in body.lower()
            or "category" in body.lower()
        ), (
            f"Invalid category {bad_category!r} must produce a visible error"
        )

    @pytest.mark.parametrize("bad_category", [
        "Clothing",
        "food",
        "",
        "'; DROP TABLE expenses;--",
    ])
    def test_invalid_category_does_not_modify_row(self, client, bad_category):
        """An invalid category must leave the expense row unchanged in the DB."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=dict(VALID_EDIT, category=bad_category))
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["category"] == row_after["category"], (
            f"Invalid category {bad_category!r} must not modify the DB row"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — date
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseDateValidation:
    """Date must be present and a valid calendar date in YYYY-MM-DD format."""

    @pytest.mark.parametrize("bad_date,label", [
        ("", "empty/missing"),
        ("not-a-date", "arbitrary string"),
        ("20-06-2026", "DD-MM-YYYY format"),
        ("06/20/2026", "MM/DD/YYYY format"),
        ("2026-13-01", "month 13"),
        ("2026-02-30", "Feb 30 does not exist"),
        ("2026-00-10", "month 0"),
        ("2026-06-00", "day 0"),
    ])
    def test_invalid_date_rerenders_form(self, client, bad_date, label):
        """A missing or malformed date must re-render the edit form (200)."""
        _login(client)
        data = dict(VALID_EDIT, date=bad_date)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 200, (
            f"Invalid date ({label}: {bad_date!r}) must re-render form (200), "
            f"got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_date,label", [
        ("", "empty/missing"),
        ("not-a-date", "arbitrary string"),
        ("2026-02-30", "Feb 30 does not exist"),
    ])
    def test_invalid_date_shows_error(self, client, bad_date, label):
        """A missing or malformed date must include a visible error message."""
        _login(client)
        data = dict(VALID_EDIT, date=bad_date)
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "valid" in body.lower()
            or "date" in body.lower()
        ), (
            f"Invalid date ({label}: {bad_date!r}) must produce a visible error"
        )

    @pytest.mark.parametrize("bad_date,label", [
        ("", "empty/missing"),
        ("not-a-date", "arbitrary string"),
        ("2026-13-01", "month 13"),
        ("2026-02-30", "Feb 30 does not exist"),
    ])
    def test_invalid_date_does_not_modify_row(self, client, bad_date, label):
        """A missing or malformed date must leave the expense row unchanged."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=dict(VALID_EDIT, date=bad_date))
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["date"] == row_after["date"], (
            f"Invalid date ({label}: {bad_date!r}) must not modify the DB row"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation errors — description
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseDescriptionValidation:
    """Description is optional but capped at 300 characters; empty stored as NULL."""

    def test_over_long_description_rerenders_form(self, client):
        """Description longer than MAX_DESCRIPTION_LENGTH must re-render the form."""
        _login(client)
        data = dict(VALID_EDIT, description="x" * (MAX_DESCRIPTION_LENGTH + 1))
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 200, (
            "Description exceeding 300 chars must re-render form (200), "
            f"got {response.status_code}"
        )

    def test_over_long_description_shows_error(self, client):
        """Description over MAX_DESCRIPTION_LENGTH must include a visible error."""
        _login(client)
        data = dict(VALID_EDIT, description="x" * (MAX_DESCRIPTION_LENGTH + 1))
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "300" in body
            or "character" in body.lower()
            or "description" in body.lower()
        ), (
            "Over-long description must produce a visible error message"
        )

    def test_over_long_description_does_not_modify_row(self, client):
        """Description over MAX_DESCRIPTION_LENGTH must not update the DB row."""
        db_path = db_module.DB_PATH
        row_before = _get_expense_row(db_path, EDIT_TARGET_ID)
        _login(client)
        client.post(
            _edit_url(EDIT_TARGET_ID),
            data=dict(VALID_EDIT, description="x" * (MAX_DESCRIPTION_LENGTH + 1)),
        )
        row_after = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row_before["description"] == row_after["description"], (
            "Over-long description must not modify the description in the DB"
        )

    def test_description_exactly_at_max_length_is_accepted(self, client):
        """Description of exactly MAX_DESCRIPTION_LENGTH characters must be accepted."""
        _login(client)
        data = dict(VALID_EDIT, description="a" * MAX_DESCRIPTION_LENGTH)
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 302, (
            f"Description of exactly {MAX_DESCRIPTION_LENGTH} chars must be accepted (302), "
            f"got {response.status_code}"
        )

    def test_empty_description_is_accepted(self, client):
        """An empty description string must be accepted (description is optional)."""
        _login(client)
        data = dict(VALID_EDIT, description="")
        response = client.post(_edit_url(EDIT_TARGET_ID), data=data)
        assert response.status_code == 302, (
            f"Empty description must not cause a validation error; expected 302, "
            f"got {response.status_code}"
        )

    def test_empty_description_stored_as_null_or_none(self, client):
        """Empty description must be stored as NULL/None in the DB, not empty string."""
        db_path = db_module.DB_PATH
        _login(client)
        client.post(_edit_url(EDIT_TARGET_ID), data=dict(VALID_EDIT, description=""))
        row = _get_expense_row(db_path, EDIT_TARGET_ID)
        assert row["description"] is None or row["description"] == "", (
            "Empty description must be stored as NULL (or empty string) in the DB, "
            f"got '{row['description']}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Input preservation on validation failure
# ─────────────────────────────────────────────────────────────────────────────

class TestEditExpenseInputPreservation:
    """On any validation failure the re-rendered form must echo the submitted values."""

    def test_submitted_amount_preserved_when_category_invalid(self, client):
        """When category is invalid, the submitted amount must appear in the form."""
        _login(client)
        data = dict(VALID_EDIT, category="BadCategory", amount="77.77")
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert "77.77" in body, (
            "Submitted amount '77.77' must appear in re-rendered form "
            "when category validation fails"
        )

    def test_submitted_category_preserved_when_amount_invalid(self, client):
        """When amount is invalid, the submitted category must appear in the form."""
        _login(client)
        data = dict(VALID_EDIT, amount="abc", category="Health")
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert "Health" in body, (
            "Submitted category 'Health' must appear in re-rendered form "
            "when amount validation fails"
        )

    def test_submitted_date_preserved_when_amount_invalid(self, client):
        """When amount is invalid, the submitted date must appear in the form."""
        _login(client)
        data = dict(VALID_EDIT, amount="abc", date="2026-09-01")
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert "2026-09-01" in body, (
            "Submitted date '2026-09-01' must appear in re-rendered form "
            "when amount validation fails"
        )

    def test_submitted_description_preserved_when_date_invalid(self, client):
        """When date is invalid, the submitted description must appear in the form."""
        _login(client)
        data = dict(VALID_EDIT, date="bad-date", description="MyPreservedNote")
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert "MyPreservedNote" in body, (
            "Submitted description must appear in re-rendered form "
            "when date validation fails"
        )

    def test_submitted_amount_preserved_when_date_invalid(self, client):
        """When date is invalid, the submitted amount must appear in the form."""
        _login(client)
        data = dict(VALID_EDIT, date="bad-date", amount="55.55")
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert "55.55" in body, (
            "Submitted amount '55.55' must appear in re-rendered form "
            "when date validation fails"
        )

    def test_submitted_category_preserved_when_date_invalid(self, client):
        """When date is invalid, the submitted category must appear in the form."""
        _login(client)
        data = dict(VALID_EDIT, date="bad-date", category="Bills")
        body = client.post(_edit_url(EDIT_TARGET_ID), data=data).get_data(as_text=True)
        assert "Bills" in body, (
            "Submitted category 'Bills' must appear in re-rendered form "
            "when date validation fails"
        )
