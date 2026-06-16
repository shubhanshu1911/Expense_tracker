from database.db import create_user, get_user_by_email
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

DEMO_USER_ID = 1


def _new_empty_user(client, name="Empty User", email="empty@example.com"):
    create_user(name, email, "password123")
    return get_user_by_email(email)["id"]


# ---------------------------------------------------------------- #
# Unit tests — query helpers
# ---------------------------------------------------------------- #

def test_get_user_by_id_valid(client):
    user = get_user_by_id(DEMO_USER_ID)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["member_since"]


def test_get_user_by_id_missing(client):
    assert get_user_by_id(99999) is None


def test_get_summary_stats_with_expenses(client):
    stats = get_summary_stats(DEMO_USER_ID)
    assert stats["total_spent"] == 6169.0
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Shopping"


def test_get_summary_stats_no_expenses(client):
    user_id = _new_empty_user(client)
    stats = get_summary_stats(user_id)
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_get_recent_transactions_with_expenses(client):
    txs = get_recent_transactions(DEMO_USER_ID)
    assert len(txs) == 8
    dates = [tx["date"] for tx in txs]
    assert dates == sorted(dates, reverse=True)
    for tx in txs:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_no_expenses(client):
    user_id = _new_empty_user(client)
    assert get_recent_transactions(user_id) == []


def test_get_category_breakdown_with_expenses(client):
    breakdown = get_category_breakdown(DEMO_USER_ID)
    assert len(breakdown) == 7
    amounts = [c["amount"] for c in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    pcts = [c["pct"] for c in breakdown]
    assert all(isinstance(p, int) for p in pcts)
    assert sum(pcts) == 100


def test_get_category_breakdown_no_expenses(client):
    user_id = _new_empty_user(client)
    assert get_category_breakdown(user_id) == []


# ---------------------------------------------------------------- #
# Route tests
# ---------------------------------------------------------------- #

def test_profile_unauthenticated_redirects_to_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "₹6,169.00" in body
    assert "Shopping" in body


def test_profile_new_user_zero_expenses(client):
    client.post(
        "/register",
        data={
            "name": "Fresh User",
            "email": "fresh@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    client.post("/login", data={"email": "fresh@example.com", "password": "password123"})
    response = client.get("/profile")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "₹0.00" in body
    assert "—" in body
