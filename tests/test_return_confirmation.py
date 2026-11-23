# Name: test_return_confirmation.py
# Description: Tests the staff return confirmation for Requirement 29
#              (Equipment Return Confirmation). Checks that a successful
#              return shows an on-screen message naming the equipment and the
#              return date, and that failed or duplicate returns never show it.
# Programmer: Karim Lakhani and Ahmed Gharib, with code-drafting assistance from Claude (Anthropic).
# Dates: November 22, 2026
# Revisions: None
# Preconditions: The seeded test database from conftest.py is available. Loan 1
#                is Student A's active Raspberry Pi Kit (KU-001) loan.
# Postconditions: Passing tests confirm the confirmation message appears only
#                 after a saved return and includes the correct item and date.
# Errors: An assertion fails if the message is missing, names the wrong item or
#         date, or appears after a rejected return.

import sqlite3

import pytest

from campusgear.db import get_record, transaction
from conftest import STAFF, get_token, login


RETURNS = "/staff/returns"
CONFIRMATION = "Equipment return recorded. Raspberry Pi Kit (KU-001) was returned on 2026-11-10."


def submit(client, **fields):
    data = dict(loan_id=1, actual_return_date="2026-11-10", condition="good",
                csrf_token=get_token(client))
    data.update(fields)
    return client.post(RETURNS, data=data, follow_redirects=True)


def test_confirmation_names_equipment_and_date(client, seeded_app):
    login(client, STAFF)
    response = submit(client)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert CONFIRMATION in html
    assert 'role="status"' in html
    # The message is shown only because the return was saved.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        assert get_record(connection, "loans", 1)["actual_return_date"] == "2026-11-10"


def test_confirmation_uses_saved_item_not_form_values(client):
    # A tampered equipment field cannot change which item the message names.
    login(client, STAFF)
    html = submit(client, equipment_id=2, equipment_name="Fake Item").get_data(as_text=True)
    assert CONFIRMATION in html and "Fake Item" not in html
    # Camera Kit still appears in the active-loan dropdown, but not in the message.
    assert "Equipment return recorded. Camera Kit" not in html


def test_confirmation_shows_only_once(client):
    login(client, STAFF)
    submit(client)
    assert "Equipment return recorded" not in client.get(RETURNS).get_data(as_text=True)


@pytest.mark.parametrize("fields", [
    {"actual_return_date": "2026-11-02"},   # before checkout
    {"actual_return_date": "bad-date"},
    {"condition": ""},
    {"loan_id": 999},
])
def test_failed_return_shows_error_not_confirmation(client, fields):
    login(client, STAFF)
    response = submit(client, **fields)
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert 'class="alert alert-error"' in html
    assert "Equipment return recorded" not in html


def test_duplicate_return_shows_error_not_confirmation(client):
    login(client, STAFF)
    assert CONFIRMATION in submit(client).get_data(as_text=True)
    response = submit(client, actual_return_date="2026-11-11")
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "already been returned" in html
    assert "Equipment return recorded" not in html


def test_database_failure_never_confirms(client, seeded_app):
    # If the save fails, the error propagates and no confirmation is queued.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        connection.execute("""
            CREATE TRIGGER reject_return BEFORE UPDATE ON equipment
            BEGIN SELECT RAISE(ABORT, 'test return failure'); END
        """)
    login(client, STAFF)
    with pytest.raises(sqlite3.IntegrityError):
        submit(client)
    with client.session_transaction() as sess:
        assert not sess.get("_flashes")
