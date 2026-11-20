"""
Module Name: test_checkout.py
Description: Checks reservation and direct checkout through the staff route.

Inputs: Test accounts, equipment, and reservations in a temporary database.
Outputs: pytest results for access, validation, and saved checkout records.

Implementation author: Codex wrote the checkout tests for Pranav Reddy.
Creation Date: November 19, 2026.
Reviewed by: Pranav Reddy.
Documentation author: Pranav Reddy.
External Sources / Attribution: Uses pytest and SQLite.
Code Origin: Newly written for EECS 581 Project 3, Requirements 11/12.
"""

import sqlite3

import pytest

from campusgear.db import get_record, insert_record, transaction
from conftest import STAFF, STUDENT_A, get_token, login


CHECKOUT = "/staff/checkout"
DATES = {"checkout_date": "2026-11-20", "due_date": "2026-11-23"}


@pytest.fixture
def checkout_data(seeded_app):
    database = seeded_app.config["DATABASE"]
    with transaction(database) as connection:
        available_id = insert_record(connection, "equipment", asset_id="KU-003",
                                     name="Tripod", category="Demo", description="")
        reserved_id = insert_record(connection, "equipment", asset_id="KU-004",
                                    name="Audio Recorder", category="Demo", description="",
                                    status="reserved")
        reservation_id = insert_record(connection, "reservations", user_id=2,
                                       equipment_id=reserved_id, pickup_date=DATES["checkout_date"],
                                       return_date=DATES["due_date"])
    return database, available_id, reserved_id, reservation_id


def submit(client, **fields):
    data = dict(DATES, csrf_token=get_token(client), checkout_type="direct", student_id=1)
    data.update(fields)
    return client.post(CHECKOUT, data=data)


def assert_checkout_saved(connection, equipment_id, student_id, reservation_id=None):
    loans = connection.execute(
        "SELECT user_id, reservation_id, checkout_date, due_date FROM loans WHERE equipment_id = ?",
        (equipment_id,)).fetchall()
    assert len(loans) == 1
    assert tuple(loans[0]) == (student_id, reservation_id, DATES["checkout_date"], DATES["due_date"])
    assert get_record(connection, "equipment", equipment_id)["status"] == "checked_out"


def test_staff_checks_out_reservation(client, checkout_data):
    database, available_id, reserved_id, reservation_id = checkout_data
    login(client, STAFF)
    assert CHECKOUT in client.get("/staff").get_data(as_text=True)
    page = client.get(CHECKOUT).get_data(as_text=True)
    assert "Student B · Audio Recorder (KU-004) · 2026-11-20 to 2026-11-23" in page
    # The saved reservation must determine the borrower and item.
    fields = dict(checkout_type="reservation", reservation_id=reservation_id,
                  equipment_id=available_id, student_id=1)
    assert submit(client, **fields).status_code == 302
    assert "Equipment checked out." in client.get(CHECKOUT).get_data(as_text=True)
    assert submit(client, **fields).status_code == 400

    with transaction(database) as connection:
        assert_checkout_saved(connection, reserved_id, student_id=2, reservation_id=reservation_id)
        assert get_record(connection, "reservations", reservation_id)["status"] == "checked_out"


def test_staff_checks_out_available_item_directly(client, checkout_data):
    database, available_id, reserved_id, _ = checkout_data
    login(client, STAFF)
    page = client.get(CHECKOUT).get_data(as_text=True)
    assert "Tripod (KU-003)" in page and STUDENT_A[1] in page
    assert STAFF[1] not in page
    assert submit(client, equipment_id=reserved_id).status_code == 400
    assert submit(client, equipment_id=available_id).status_code == 302
    assert submit(client, equipment_id=available_id).status_code == 400

    with transaction(database) as connection:
        assert_checkout_saved(connection, available_id, student_id=1)


@pytest.mark.parametrize("fields", [
    {"due_date": "2026-02-30"}, {"due_date": DATES["checkout_date"]}, {"student_id": 3},
    {"equipment_id": 999}, {"equipment_id": 1}, {"csrf_token": ""},
    {"checkout_type": "reservation", "reservation_id": 999},
])
def test_invalid_checkout_does_not_write(client, checkout_data, fields):
    database, available_id, _, _ = checkout_data
    login(client, STAFF)
    data = {"equipment_id": available_id, **fields}
    assert submit(client, **data).status_code == 400
    with transaction(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM loans").fetchone()[0] == 2
        assert get_record(connection, "equipment", available_id)["status"] == "available"


def test_cancelling_reservation_unblocks_direct_checkout(client, checkout_data):
    database, _, reserved_id, reservation_id = checkout_data
    with transaction(database) as connection:
        connection.execute("UPDATE equipment SET status = 'available' WHERE id = ?", (reserved_id,))
    login(client, STAFF)
    assert submit(client, equipment_id=reserved_id).status_code == 400
    with transaction(database) as connection:
        connection.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
    assert submit(client, checkout_type="reservation", reservation_id=reservation_id).status_code == 400
    assert submit(client, equipment_id=reserved_id).status_code == 302


def test_checkout_is_staff_only(client):
    assert client.get(CHECKOUT).status_code == 302
    login(client, STUDENT_A)
    assert client.get(CHECKOUT).status_code == 403
    assert submit(client).status_code == 403


def test_checkout_rolls_back_when_status_update_fails(client, checkout_data):
    database, _, reserved_id, reservation_id = checkout_data
    with transaction(database) as connection:
        # Force the last update to fail after the loan and equipment changes.
        connection.execute("""
            CREATE TRIGGER reject_checkout BEFORE UPDATE ON reservations
            BEGIN SELECT RAISE(ABORT, 'test update failure'); END
        """)
    login(client, STAFF)
    with pytest.raises(sqlite3.IntegrityError, match="test update failure"):
        submit(client, checkout_type="reservation", reservation_id=reservation_id)
    with transaction(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM loans").fetchone()[0] == 2
        assert get_record(connection, "equipment", reserved_id)["status"] == "reserved"
        assert get_record(connection, "reservations", reservation_id)["status"] == "reserved"
