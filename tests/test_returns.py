"""Requirement 13 return workflow tests, written with OpenAI Codex assistance."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from campusgear.business_logic.loan_management import ReturnError, return_equipment
from campusgear.db import get_record, transaction
from conftest import STAFF, STUDENT_A, get_token, login


RETURNS = "/staff/returns"


def submit(client, **fields):
    data = dict(loan_id=1, actual_return_date="2026-11-10", condition="good",
                csrf_token=get_token(client))
    data.update(fields)
    return client.post(RETURNS, data=data)


def snapshot(database):
    with transaction(database) as connection:
        return {table: [tuple(row) for row in connection.execute(
            f"SELECT * FROM {table} ORDER BY id")]
                for table in ("loans", "equipment", "reservations")}


@pytest.mark.parametrize("condition,status", [
    ("good", "available"), ("damaged", "maintenance"), ("needs_repair", "maintenance"),
])
@pytest.mark.parametrize("linked", [False, True])
def test_return_saves_loan_and_equipment(client, seeded_app, condition, status, linked):
    database = seeded_app.config["DATABASE"]
    if linked:
        with transaction(database) as connection:
            connection.execute("UPDATE loans SET reservation_id = 1 WHERE id = 1")
    before = snapshot(database)
    login(client, STAFF)
    assert RETURNS in client.get("/staff").get_data(as_text=True)
    page = client.get(RETURNS).get_data(as_text=True)
    assert "Student A" in page and "Raspberry Pi Kit (KU-001)" in page
    # Submitted equipment, borrower, reservation, and status fields cannot override the loan.
    assert submit(client, condition=condition, equipment_id=2, user_id=2,
                  reservation_id=2, status="available").status_code == 302
    page = client.get(RETURNS).get_data(as_text=True)
    assert "Equipment return recorded." in page
    assert 'value="1"' not in page and 'value="2"' in page
    with transaction(database) as connection:
        loan = get_record(connection, "loans", 1)
        item = get_record(connection, "equipment", 1)
        assert (loan["status"], loan["actual_return_date"]) == ("returned", "2026-11-10")
        assert (item["condition"], item["status"]) == (condition, status)
        assert get_record(connection, "loans", 2)["status"] == "checked_out"
        assert get_record(connection, "equipment", 2)["status"] == "checked_out"
    assert snapshot(database)["reservations"] == before["reservations"]
    saved = snapshot(database)
    assert submit(client, condition="damaged", actual_return_date="2026-11-11").status_code == 400
    assert snapshot(database) == saved


@pytest.mark.parametrize("fields", [
    {"actual_return_date": ""}, {"actual_return_date": "not-a-date"},
    {"actual_return_date": "2026-02-30"}, {"actual_return_date": "20261110"},
    {"actual_return_date": "2026-11-02"}, {"condition": ""}, {"condition": "unknown"},
    {"loan_id": ""}, {"loan_id": "abc"}, {"loan_id": 999},
    {"csrf_token": ""}, {"csrf_token": "wrong"},
])
def test_invalid_return_does_not_write(client, seeded_app, fields):
    login(client, STAFF)
    before = snapshot(seeded_app.config["DATABASE"])
    assert submit(client, **fields).status_code == 400
    assert snapshot(seeded_app.config["DATABASE"]) == before


def test_return_preserves_valid_fields_after_validation_error(client):
    login(client, STAFF)
    response = submit(client, actual_return_date="2026-11-02", condition="damaged")
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Return date cannot be before the checkout date." in page
    assert 'value="2026-11-02"' in page
    assert 'value="damaged" selected' in page
    assert 'value="1" selected' in page


def test_return_on_checkout_date_is_allowed(client):
    login(client, STAFF)
    assert submit(client, actual_return_date="2026-11-03").status_code == 302


def test_returns_are_staff_only(client, seeded_app):
    before = snapshot(seeded_app.config["DATABASE"])
    assert client.get(RETURNS).status_code == 302
    assert submit(client).status_code == 302
    login(client, STUDENT_A)
    assert client.get(RETURNS).status_code == 403
    assert submit(client).status_code == 403
    assert snapshot(seeded_app.config["DATABASE"]) == before


def test_no_active_loans(client, seeded_app):
    login(client, STAFF)
    assert submit(client).status_code == 302
    assert submit(client, loan_id=2).status_code == 302
    page = client.get(RETURNS).get_data(as_text=True)
    assert "No active loans" in page and "disabled" in page


def test_return_rolls_back_when_equipment_update_fails(client, seeded_app):
    database = seeded_app.config["DATABASE"]
    with transaction(database) as connection:
        connection.execute("""
            CREATE TRIGGER reject_return BEFORE UPDATE ON equipment
            BEGIN SELECT RAISE(ABORT, 'test return failure'); END
        """)
    before = snapshot(database)
    login(client, STAFF)
    with pytest.raises(sqlite3.IntegrityError, match="test return failure"):
        submit(client)
    assert snapshot(database) == before


def test_competing_returns_save_once(seeded_app):
    def attempt(condition):
        with seeded_app.app_context():
            try:
                return_equipment(dict(loan_id=1, actual_return_date="2026-11-10",
                                      condition=condition))
            except ReturnError:
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ["good", "damaged"]))
    assert sorted(results) == [False, True]
    with transaction(seeded_app.config["DATABASE"]) as connection:
        item = get_record(connection, "equipment", 1)
        assert (item["condition"], item["status"]) == (
            ("good", "available") if results[0] else ("damaged", "maintenance"))
        assert get_record(connection, "loans", 1)["status"] == "returned"
