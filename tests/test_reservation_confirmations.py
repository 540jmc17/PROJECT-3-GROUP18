# Name: test_reservation_confirmations.py
# Description: Tests the messages students see after creating or canceling
#              an equipment reservation. Checks that a successful action
#              shows its confirmation on the records page and that the
#              message disappears when the student loads the page again.
#              Also checks rejected requests and simulates a database
#              failure during both creation and cancellation.
# Programmer: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
# Dates: November 19, 2026
# Preconditions: The Flask test client and seeded test database are available.
#                The seed data includes Student A, a staff account, a checked-out
#                reservation, and a reservation belonging to Student B.
#                Test helpers provide login, logout, and CSRF tokens.
# Postconditions: Passing tests confirm that successful actions display the
#                 expected messages and save the expected reservation status.
#                 When a database write fails, the student sees an error and
#                 the database retains its state from before the attempt.
# Errors: An assertion fails if a message is missing, repeats on the next
#         page load, or reports success for a failed write. Assertions also
#         check access restrictions and the stored reservation records.

from contextlib import contextmanager
from datetime import date
from sqlite3 import OperationalError

import pytest

from campusgear.db import insert_record, transaction
from conftest import STAFF, STUDENT_A, get_token, login, logout


# Student A has user ID 1 in the test database.
RECORDS = "/students/1/records"

# Flask's response.data contains bytes. The b prefix lets the tests search
# those bytes for the exact message the student should see.
CREATED = b"Reservation created successfully."
CANCELED = b"Reservation canceled successfully."


@pytest.fixture
def reservable_item(seeded_app, monkeypatch):
    # A fixture prepares data for a test. Monkeypatch temporarily makes
    # the route treat November 17 as today so the test dates stay predictable.
    monkeypatch.setattr("campusgear.presentation.student.reservation_today",
                        lambda: date(2026, 11, 17))

    # Add a Tripod to the test database. Tests that request reservable_item
    # receive its equipment ID, which they use to build the reservation URL.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        return insert_record(connection, "equipment", asset_id="KU-003",
                             name="Tripod", category="Demo", description="Test item")


def submit_reservation(client, equipment_id, end="2026-11-20"):
    # Submit the reservation form with the client's CSRF token. Tests can
    # override the end date to use the same form with invalid input.
    # follow_redirects=True lets the test read the page the student lands on.
    return client.post(f"/catalog/{equipment_id}/reserve", data={
        "csrf_token": get_token(client), "start_date": "2026-11-17", "end_date": end,
    }, follow_redirects=True)


def submit_cancellation(client, reservation_id):
    # Cancellation uses the reservation ID because the student is acting
    # on a specific booking. Follow the redirect to read the result message.
    return client.post(f"/student/reservations/{reservation_id}/cancel",
                       data={"csrf_token": get_token(client)}, follow_redirects=True)


def test_create_and_cancel_confirm_only_after_saving(client, seeded_app, reservable_item):
    login(client, STUDENT_A)
    response = submit_reservation(client, reservable_item)

    # The first response is the page reached after submitting the form.
    # A separate GET simulates refreshing it. The confirmation should
    # appear on that first visit and be gone on the refresh.
    assert response.request.path == RECORDS
    assert CREATED in response.data
    assert CREATED not in client.get(RECORDS).data

    # Check the saved row as well as the message. Keep its reservation ID
    # so the cancellation below acts on the booking we just created.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        row = connection.execute(
            "SELECT id, status FROM reservations WHERE equipment_id = ?", (reservable_item,),
        ).fetchone()
        assert row["status"] == "reserved"
        reservation_id = row["id"]

    # The original records page should contain this booking's cancellation
    # URL. encode() converts the URL to bytes for comparison with response.data.
    assert f'/student/reservations/{reservation_id}/cancel'.encode() in response.data
    response = submit_cancellation(client, reservation_id)

    # The student should see the cancellation confirmation once. The earlier
    # creation message should also be gone.
    assert CANCELED in response.data
    assert CREATED not in response.data
    assert CANCELED not in client.get(RECORDS).data

    # Cancellation keeps the reservation row and changes its stored status.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        row = connection.execute("SELECT status FROM reservations WHERE id = ?",
                                 (reservation_id,)).fetchone()
        assert row["status"] == "cancelled"

    # Try canceling the same booking a second time. The response should
    # show that it cannot be canceled again.
    assert b"This reservation cannot be canceled." in submit_cancellation(
        client, reservation_id).data
    assert CANCELED not in client.get(RECORDS).data


def test_failed_validation_and_ineligible_cancellations_show_errors(client, reservable_item):
    login(client, STUDENT_A)

    # The helper already uses November 17 as the start date. Giving it the
    # same end date should produce a date error and no creation confirmation.
    response = submit_reservation(client, reservable_item, end="2026-11-17")
    assert b"end date must be later" in response.data
    assert CREATED not in response.data

    # ID 1 is already checked out, ID 2 belongs to Student B, and ID 999
    # represents a missing reservation in the test data.
    for reservation_id in (1, 2, 999):
        response = submit_cancellation(client, reservation_id)
        assert b"This reservation cannot be canceled." in response.data
        assert CANCELED not in response.data

    # Posting directly skips the helper that supplies the CSRF token.
    # The route should reject the missing token with HTTP 400.
    assert client.post("/student/reservations/1/cancel").status_code == 400

    # The cancellation request should return 403,
    # and the records page should omit this reservation's cancellation URL.
    logout(client)
    login(client, STAFF)
    assert client.post("/student/reservations/1/cancel").status_code == 403
    assert b"/student/reservations/1/cancel" not in client.get(RECORDS).data


def test_write_failure_rolls_back_and_never_confirms(
        client, seeded_app, reservable_item, monkeypatch):
    # Save one reservation before simulating any failures. At the end of
    # the test, this exact reservation should still exist as "reserved".
    with transaction(seeded_app.config["DATABASE"]) as connection:
        reservation_id = insert_record(
            connection, "reservations", user_id=1, equipment_id=reservable_item,
            pickup_date="2026-11-17", return_date="2026-11-20",
        )

    @contextmanager
    def fail_before_commit(path):
        # yield hands the open connection to the reservation code so it can
        # perform its write. When that code finishes, execution resumes at
        # raise, just before the transaction would normally commit.
        with transaction(path) as connection:
            yield connection
            raise OperationalError("simulated write failure")

    # Only the reservation module uses the failing transaction helper.
    # This test can still use its own transaction helper to inspect the
    # database afterward. pytest restores the patched helper after the test.
    monkeypatch.setattr("campusgear.business_logic.reservation_management.transaction",
                        fail_before_commit)

    # Attempt to create a reservation. The simulated database failure should
    # produce HTTP 500, a save error, and no creation confirmation.
    login(client, STUDENT_A)
    response = submit_reservation(client, reservable_item)
    assert response.status_code == 500
    assert b"Could not save your reservation" in response.data
    assert CREATED not in response.data

    # The records page should show a cancellation error and no success confirmation.
    response = submit_cancellation(client, reservation_id)
    assert b"Could not cancel your reservation" in response.data
    assert CANCELED not in response.data

    # Read every reservation for the Tripod. Exactly one row should remain,
    # the original ID with its original "reserved" status. This checks both
    # rollbacks.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        rows = connection.execute(
            "SELECT id, status FROM reservations WHERE equipment_id = ?", (reservable_item,),
        ).fetchall()
        assert [tuple(row) for row in rows] == [(reservation_id, "reserved")]