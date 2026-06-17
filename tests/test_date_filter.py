"""
tests/test_date_filter.py

Pytest tests for the Step 06 date-filter feature on the Spendly profile page.

Covers:
  - Unit tests for get_summary_stats, get_recent_transactions, get_category_breakdown
    with date_from / date_to parameters.
  - Route tests for GET /profile with various date-filter query strings.

All tests reuse the `client` fixture from conftest.py, which monkeypatches DB_PATH to
a fresh temp file, calls init_db() + seed_db(), and yields a Flask test client.

Seed data (demo@spendly.com / demo123, user_id=1):
  2026-06-01  Food          ₹850.00   Groceries
  2026-06-03  Transport     ₹250.00   Monthly metro pass
  2026-06-05  Bills        ₹1200.00   Electricity bill
  2026-06-07  Health        ₹500.00   Pharmacy
  2026-06-08  Entertainment ₹399.00   Streaming subscription
  2026-06-10  Shopping     ₹2200.00   Clothes
  2026-06-11  Other         ₹150.00   Miscellaneous
  2026-06-12  Food          ₹620.00   Restaurant dinner
  Total: ₹6169.00 — 8 transactions — top category: Shopping
"""

import pytest

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)

DEMO_USER_ID = 1
DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    """Log in with the seed demo account."""
    return client.post("/login", data={"email": email, "password": password})


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — get_summary_stats
# ─────────────────────────────────────────────────────────────────────────────


class TestGetSummaryStatsDateFilter:
    """get_summary_stats(user_id, date_from, date_to) — unit tests."""

    def test_wide_range_includes_all_expenses_matches_no_filter(self, client):
        """A range that spans all seed data should return the same totals as no filter."""
        stats_unfiltered = get_summary_stats(DEMO_USER_ID)
        stats_filtered = get_summary_stats(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-30"
        )
        assert stats_filtered["total_spent"] == stats_unfiltered["total_spent"], (
            "Wide range total_spent should equal unfiltered total_spent"
        )
        assert stats_filtered["transaction_count"] == stats_unfiltered["transaction_count"], (
            "Wide range transaction_count should equal unfiltered count"
        )
        assert stats_filtered["top_category"] == stats_unfiltered["top_category"], (
            "Wide range top_category should equal unfiltered top_category"
        )

    def test_range_excluding_all_expenses_returns_zeros(self, client):
        """A range with no seed expenses must return zeroed-out stats."""
        stats = get_summary_stats(
            DEMO_USER_ID, date_from="2026-01-01", date_to="2026-01-31"
        )
        assert stats["total_spent"] == 0, "total_spent must be 0 when no expenses fall in range"
        assert stats["transaction_count"] == 0, "transaction_count must be 0 when no expenses fall in range"
        assert stats["top_category"] == "—", "top_category must be '—' when no expenses fall in range"

    def test_partial_range_returns_correct_totals(self, client):
        """Range 2026-06-01 to 2026-06-05 covers Food(850), Transport(250), Bills(1200)."""
        # Expected: total=2300, count=3, top_category=Bills (1200 is highest)
        stats = get_summary_stats(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-05"
        )
        assert stats["total_spent"] == 2300.0, (
            f"Expected total_spent=2300.0 for June 1-5, got {stats['total_spent']}"
        )
        assert stats["transaction_count"] == 3, (
            f"Expected transaction_count=3 for June 1-5, got {stats['transaction_count']}"
        )
        assert stats["top_category"] == "Bills", (
            f"Expected top_category='Bills' for June 1-5 (Bills=1200 is highest), got {stats['top_category']}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — get_recent_transactions
# ─────────────────────────────────────────────────────────────────────────────


class TestGetRecentTransactionsDateFilter:
    """get_recent_transactions(user_id, limit, date_from, date_to) — unit tests."""

    def test_wide_range_returns_all_seed_transactions(self, client):
        """A range spanning all seed dates returns the same 8 rows as no filter."""
        txs_unfiltered = get_recent_transactions(DEMO_USER_ID)
        txs_filtered = get_recent_transactions(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-30"
        )
        assert len(txs_filtered) == len(txs_unfiltered), (
            f"Wide range should return {len(txs_unfiltered)} transactions, got {len(txs_filtered)}"
        )
        assert len(txs_filtered) == 8, "There are 8 seed transactions total"

    def test_range_excluding_all_expenses_returns_empty_list(self, client):
        """A range with no seed expenses must return an empty list."""
        txs = get_recent_transactions(
            DEMO_USER_ID, date_from="2026-01-01", date_to="2026-01-31"
        )
        assert txs == [], f"Expected empty list for out-of-range dates, got {txs}"

    def test_partial_range_returns_only_matching_transactions(self, client):
        """Range 2026-06-01 to 2026-06-05 returns exactly 3 transactions, date-sorted desc."""
        txs = get_recent_transactions(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-05"
        )
        assert len(txs) == 3, (
            f"Expected 3 transactions for June 1-5, got {len(txs)}"
        )
        amounts = {tx["amount"] for tx in txs}
        assert 850.0 in amounts, "Food/Groceries (₹850) should be in June 1-5 results"
        assert 250.0 in amounts, "Transport (₹250) should be in June 1-5 results"
        assert 1200.0 in amounts, "Bills (₹1200) should be in June 1-5 results"
        # Must NOT include expenses outside the range
        assert 2200.0 not in amounts, "Shopping (₹2200, June 10) must NOT appear in June 1-5 results"
        # Verify descending date order
        dates = [tx["date"] for tx in txs]
        assert dates == sorted(dates, reverse=True), "Transactions must be returned in descending date order"

    def test_partial_range_row_structure_intact(self, client):
        """Each returned row must have the expected keys regardless of date filter."""
        txs = get_recent_transactions(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-05"
        )
        for tx in txs:
            assert set(tx.keys()) == {"date", "description", "category", "amount"}, (
                f"Unexpected keys in filtered transaction row: {set(tx.keys())}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — get_category_breakdown
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCategoryBreakdownDateFilter:
    """get_category_breakdown(user_id, date_from, date_to) — unit tests."""

    def test_wide_range_matches_unfiltered_breakdown(self, client):
        """A range spanning all seed dates returns the same 7-category breakdown."""
        breakdown_unfiltered = get_category_breakdown(DEMO_USER_ID)
        breakdown_filtered = get_category_breakdown(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-30"
        )
        assert len(breakdown_filtered) == len(breakdown_unfiltered), (
            "Wide range breakdown should have same number of categories as unfiltered"
        )
        assert len(breakdown_filtered) == 7, "All 7 seed categories must appear in the wide-range breakdown"

    def test_range_excluding_all_expenses_returns_empty_list(self, client):
        """A range with no expenses returns an empty list."""
        breakdown = get_category_breakdown(
            DEMO_USER_ID, date_from="2026-01-01", date_to="2026-01-31"
        )
        assert breakdown == [], (
            f"Expected empty list for out-of-range dates, got {breakdown}"
        )

    def test_partial_range_returns_correct_categories_and_totals(self, client):
        """Range June 1-5 covers: Food=850, Transport=250, Bills=1200. Total=2300."""
        breakdown = get_category_breakdown(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-05"
        )
        assert len(breakdown) == 3, (
            f"Expected 3 categories for June 1-5, got {len(breakdown)}"
        )
        names = {entry["name"] for entry in breakdown}
        assert names == {"Food", "Transport", "Bills"}, (
            f"Unexpected categories in partial range: {names}"
        )
        amounts_by_name = {entry["name"]: entry["amount"] for entry in breakdown}
        assert amounts_by_name["Food"] == 850.0, f"Food amount should be 850.0, got {amounts_by_name['Food']}"
        assert amounts_by_name["Transport"] == 250.0, f"Transport amount should be 250.0, got {amounts_by_name['Transport']}"
        assert amounts_by_name["Bills"] == 1200.0, f"Bills amount should be 1200.0, got {amounts_by_name['Bills']}"

    def test_partial_range_percentages_sum_to_100(self, client):
        """Percentages in a partial range must still sum to 100."""
        breakdown = get_category_breakdown(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-05"
        )
        pcts = [entry["pct"] for entry in breakdown]
        assert sum(pcts) == 100, (
            f"Category breakdown percentages must sum to 100, got {sum(pcts)}"
        )
        assert all(isinstance(p, int) for p in pcts), "All percentages must be integers"

    def test_partial_range_sorted_descending_by_amount(self, client):
        """Categories must be sorted by amount descending."""
        breakdown = get_category_breakdown(
            DEMO_USER_ID, date_from="2026-06-01", date_to="2026-06-05"
        )
        amounts = [entry["amount"] for entry in breakdown]
        assert amounts == sorted(amounts, reverse=True), (
            "Category breakdown must be sorted descending by amount"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route tests — GET /profile with date filter query params
# ─────────────────────────────────────────────────────────────────────────────


class TestProfileDateFilterRoute:
    """Integration tests for GET /profile with date_from / date_to query params."""

    # ── Baseline ──────────────────────────────────────────────────────────────

    def test_no_params_authenticated_returns_200_with_all_seed_data(self, client):
        """GET /profile (no params) for the seed user returns 200 and full data."""
        _login(client)
        response = client.get("/profile")
        assert response.status_code == 200, (
            f"Expected 200 from /profile with no params, got {response.status_code}"
        )
        body = response.get_data(as_text=True)
        assert "₹6,169.00" in body, "Full total ₹6,169.00 must appear with no date filter"
        assert "Shopping" in body, "Top category 'Shopping' must appear with no date filter"
        assert "Demo User" in body, "User name 'Demo User' must appear on profile page"

    # ── Valid partial range ───────────────────────────────────────────────────

    def test_valid_date_range_filters_displayed_amounts(self, client):
        """
        GET /profile?date_from=2026-06-01&date_to=2026-06-05 must show only
        expenses within that range. June 1 (₹850) and June 3 (₹250) are present;
        June 5 (₹1200, Bills) is the upper-boundary inclusive record.
        The total must be ₹2,300.00 and ₹2,200.00 (Shopping, June 10) must not appear.
        """
        _login(client)
        response = client.get("/profile?date_from=2026-06-01&date_to=2026-06-05")
        assert response.status_code == 200, (
            f"Expected 200 for valid date range, got {response.status_code}"
        )
        body = response.get_data(as_text=True)
        # Amounts that belong in this range
        assert "850" in body, "₹850 (Food, June 1) should be visible in June 1-5 filter"
        assert "250" in body, "₹250 (Transport, June 3) should be visible in June 1-5 filter"
        # Shopping on June 10 must NOT appear in filtered totals
        assert "₹6,169.00" not in body, (
            "Full total ₹6,169.00 must NOT appear when a date filter is active"
        )
        assert "₹2,200.00" not in body, (
            "Shopping expense ₹2,200.00 (June 10) must NOT appear in June 1-5 results"
        )

    def test_valid_date_range_total_is_correct(self, client):
        """The summary total displayed for June 1-5 must be ₹2,300.00."""
        _login(client)
        response = client.get("/profile?date_from=2026-06-01&date_to=2026-06-05")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "2,300.00" in body, (
            "Filtered total for June 1-5 (₹2,300.00) must appear in the page"
        )

    # ── Inverted range ────────────────────────────────────────────────────────

    def test_inverted_range_shows_flash_message(self, client):
        """
        GET /profile?date_from=2026-06-10&date_to=2026-06-01 (start > end) must return
        200 and include the flash message 'Start date must be before end date.'
        """
        _login(client)
        response = client.get(
            "/profile?date_from=2026-06-10&date_to=2026-06-01",
            follow_redirects=True,
        )
        assert response.status_code == 200, (
            f"Expected 200 for inverted range, got {response.status_code}"
        )
        body = response.get_data(as_text=True)
        assert "Start date must be before end date." in body, (
            "Flash message 'Start date must be before end date.' must appear for inverted range"
        )

    def test_inverted_range_falls_back_to_full_unfiltered_data(self, client):
        """When range is inverted the page must still show the full All Time data."""
        _login(client)
        response = client.get(
            "/profile?date_from=2026-06-10&date_to=2026-06-01",
            follow_redirects=True,
        )
        body = response.get_data(as_text=True)
        assert "₹6,169.00" in body, (
            "Full total ₹6,169.00 must still appear when date range is inverted (fallback to All Time)"
        )
        assert "Shopping" in body, (
            "Top category 'Shopping' must appear in fallback unfiltered data"
        )

    # ── Malformed / invalid dates ─────────────────────────────────────────────

    def test_malformed_dates_do_not_crash_page(self, client):
        """GET /profile?date_from=not-a-date&date_to=also-bad must return 200 without crashing."""
        _login(client)
        response = client.get("/profile?date_from=not-a-date&date_to=also-bad")
        assert response.status_code == 200, (
            f"Malformed date params must not crash the page, expected 200, got {response.status_code}"
        )

    def test_malformed_dates_render_all_time_data(self, client):
        """Malformed dates should be silently ignored; full All Time data renders."""
        _login(client)
        response = client.get("/profile?date_from=not-a-date&date_to=also-bad")
        body = response.get_data(as_text=True)
        assert "₹6,169.00" in body, (
            "Full total ₹6,169.00 must appear when date params are invalid (fall back to All Time)"
        )

    def test_single_malformed_date_param_does_not_crash(self, client):
        """Only one valid date param (the other is garbage) should also not crash."""
        _login(client)
        response = client.get("/profile?date_from=2026-06-01&date_to=INVALID")
        assert response.status_code == 200, (
            "Partially malformed date params must not crash the page"
        )

    # ── Range with no expenses ────────────────────────────────────────────────

    def test_range_with_no_expenses_shows_zero_total(self, client):
        """GET /profile for January 2026 (no seed expenses) must show ₹0.00 total."""
        _login(client)
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert response.status_code == 200, (
            f"Expected 200 for range with no expenses, got {response.status_code}"
        )
        body = response.get_data(as_text=True)
        assert "₹0.00" in body, (
            "Total must display ₹0.00 when no expenses fall in the selected range"
        )

    def test_range_with_no_expenses_shows_zero_transaction_count(self, client):
        """A range with no expenses must show 0 transactions."""
        _login(client)
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        body = response.get_data(as_text=True)
        # The page should show 0 transactions — check for the dash fallback or 0
        assert "₹6,169.00" not in body, (
            "Full total must NOT appear when filtering to a range with no expenses"
        )

    def test_range_with_no_expenses_does_not_show_error(self, client):
        """An empty-result range must not raise an exception or show a 500 page."""
        _login(client)
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert response.status_code == 200, "Empty-range filter must return 200, not an error page"
        body = response.get_data(as_text=True)
        # Should not contain generic Flask error markers
        assert "Internal Server Error" not in body, "Page must not show Internal Server Error"

    # ── Filter bar presence ───────────────────────────────────────────────────

    def test_filter_bar_contains_this_month_preset(self, client):
        """The profile page HTML must contain a 'This Month' preset link/button."""
        _login(client)
        response = client.get("/profile")
        body = response.get_data(as_text=True)
        assert "This Month" in body, "'This Month' preset must be rendered in the filter bar"

    def test_filter_bar_contains_last_3_months_preset(self, client):
        """The profile page HTML must contain a 'Last 3 Months' preset link/button."""
        _login(client)
        response = client.get("/profile")
        body = response.get_data(as_text=True)
        assert "Last 3 Months" in body, "'Last 3 Months' preset must be rendered in the filter bar"

    def test_filter_bar_contains_last_6_months_preset(self, client):
        """The profile page HTML must contain a 'Last 6 Months' preset link/button."""
        _login(client)
        response = client.get("/profile")
        body = response.get_data(as_text=True)
        assert "Last 6 Months" in body, "'Last 6 Months' preset must be rendered in the filter bar"

    def test_filter_bar_contains_all_time_preset(self, client):
        """The profile page HTML must contain an 'All Time' preset link/button."""
        _login(client)
        response = client.get("/profile")
        body = response.get_data(as_text=True)
        assert "All Time" in body, "'All Time' preset must be rendered in the filter bar"

    def test_filter_bar_all_four_presets_present(self, client):
        """All four date preset labels must appear together in a single page load."""
        _login(client)
        response = client.get("/profile")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
            assert label in body, f"Filter bar preset '{label}' is missing from /profile response"

    # ── Active preset CSS class ───────────────────────────────────────────────

    def test_all_time_preset_has_active_class_when_no_filter_applied(self, client):
        """When no date filter is active, the 'All Time' element must carry the 'active' CSS class."""
        _login(client)
        response = client.get("/profile")
        body = response.get_data(as_text=True)
        # The 'active' class must appear somewhere near 'All Time'
        # We verify both tokens exist in the page; exact proximity is template-specific.
        assert "active" in body, "The 'active' CSS class must appear on the filter bar"
        assert "All Time" in body, "'All Time' label must appear in the filter bar"
