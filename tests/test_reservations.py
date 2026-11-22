# Name: test_reservations.py
# Description: Tests how a student selects pickup and return dates for
#              an equipment reservation. Follows a successful booking
#              from the catalog link through the form to the saved record.
#              Also covers invalid dates, student-only access, a missing
#              CSRF token, and equipment becoming unavailable before submission.
# Programmer: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
# Dates: November 19, 2026
# Preconditions: The Flask test client and seeded test database are available.
#                The test data includes Student A (user ID 1), a staff account,
#                and equipment used by the catalog. Helpers provide login and
#                CSRF tokens. The fixture below adds a Tripod for each case.
# Postconditions: Passing tests confirm that a valid booking saves the Tripod,
#                 signed-in borrower, selected dates, and initial "reserved"
#                 status together. Invalid dates and a switch to maintenance
#                 leave zero reservations for the Tripod. Access checks verify
#                 the responses for guests, staff, and a missing CSRF token.
# Errors: An assertion fails if a page shows unexpected form fields, links,
#         dates, or response codes, or if the saved reservation data differs
#         from what the student was allowed to book.

from datetime import date

import pytest

from campusgear.db import insert_record, transaction
from conftest import STAFF, STUDENT_A, get_token, login


@pytest.fixture
def available_equipment(seeded_app, monkeypatch):
    # Make the reservation route treat November 17 as today so "yesterday"
    # and "today" mean the same thing whenever someone runs these tests.
    monkeypatch.setattr("campusgear.presentation.student.reservation_today",
                        lambda: date(2026, 11, 17))

    # Insert a Tripod into the test database. The returned equipment ID
    # becomes the value of available_equipment inside each test.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        return insert_record(connection, "equipment", asset_id="KU-003",
                             name="Tripod", category="Demo", description="Test item")


def test_student_reserves_available_equipment_from_catalog(client, seeded_app,
                                                           available_equipment):
    # Sign in and open the catalog.
    # The catalog should link to the Tripod's form and leave out the reservation
    # URL for equipment ID 1 in the seeded data.
    login(client, STUDENT_A)
    url = f"/catalog/{available_equipment}/reserve"
    catalog = client.get("/catalog").get_data(as_text=True)
    assert f'href="{url}"' in catalog
    assert "/catalog/1/reserve" not in catalog

    # GET opens the form. Check that it loads (200), contains both date
    # fields, and includes today's date as an HTML minimum. The b prefix
    # lets us search form.data.
    form = client.get(url)
    assert form.status_code == 200
    assert b'name="start_date"' in form.data
    assert b'name="end_date"' in form.data
    assert b'min="2026-11-17"' in form.data

    # POST submits a valid booking from November 17 to November 20.
    # The saved borrower should still be Student A (ID 1).
    response = client.post(url, data={
        "csrf_token": get_token(client), "start_date": "2026-11-17",
        "end_date": "2026-11-20", "user_id": 2,
    }, follow_redirects=True)

    # follow_redirects=True gives us the final page. history[0] lets us
    # check the first response, a 303 telling the client to load
    # another page. Student A should land on their records and see both dates.
    assert response.history[0].status_code == 303
    assert response.request.path == "/students/1/records"
    assert b"2026-11-17" in response.data
    assert b"2026-11-20" in response.data

    # Look up the booking by the Tripod's ID. The values in tuple(row)
    # follow the SELECT order.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        row = connection.execute(
            "SELECT user_id, pickup_date, return_date, status FROM reservations "
            "WHERE equipment_id = ?", (available_equipment,),
        ).fetchone()
        assert tuple(row) == (1, "2026-11-17", "2026-11-20", "reserved")


# pytest runs the function below once per row. Each row gives it a start
# date, an end date, and the error text expected for that particular input.
@pytest.mark.parametrize(("start", "end", "error"), [
    ("2026-11-16", "2026-11-20", b"cannot be in the past"),  # Yesterday
    ("2026-11-17", "2026-11-17", b"must be later"),          # Same day
    ("2026-11-20", "2026-11-17", b"must be later"),          # Return before pickup
    ("2026-02-30", "2026-11-20", b"valid start date"),       # February 30
    ("20261117", "2026-11-20", b"valid start date"),         # Missing hyphens
    (None, "2026-11-20", b"valid start date"),               # Missing start
    ("2026-11-17", None, b"valid end date"),                 # Missing end
])
def test_invalid_dates_show_error_without_saving(client, seeded_app, available_equipment,
                                                  start, end, error):
    login(client, STUDENT_A)

    # Include a valid CSRF token so each request reaches date validation.
    # Add only the dates supplied by this case.
    form = {"csrf_token": get_token(client)}
    form.update({key: value for key, value in (("start_date", start), ("end_date", end))
                 if value is not None})

    # Posting directly uses the server's validation for dates
    # that a browser's date picker might prevent a student from selecting.
    response = client.post(f"/catalog/{available_equipment}/reserve", data=form)
    assert response.status_code == 400
    assert error in response.data

    # COUNT(*) returns one row containing the count. fetchone()[0] reads
    # that number.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM reservations WHERE equipment_id = ?", (available_equipment,),
        ).fetchone()[0] == 0


def test_form_and_submission_require_student_role_and_post_requires_csrf(
        client, available_equipment):
    url = f"/catalog/{available_equipment}/reserve"

    # Start as a guest. Opening the form (GET) and submitting it (POST)
    # should both produce a redirect (302).
    assert client.get(url).status_code == 302
    assert client.post(url).status_code == 302

    # Staff receive 403 (Forbidden) for both requests. Also check that the
    # catalog shown to staff leaves out the Tripod's reservation link.
    login(client, STAFF)
    assert client.get(url).status_code == 403
    assert client.post(url).status_code == 403
    assert f'href="{url}"' not in client.get("/catalog").get_data(as_text=True)

    # Student A has the required role and supplies valid dates, but this
    # form omits the CSRF token. The expected response is 400.
    login(client, STUDENT_A)
    assert client.post(url, data={
        "start_date": "2026-11-17", "end_date": "2026-11-20",
    }).status_code == 400


def test_equipment_becoming_unavailable_prevents_reservation(client, seeded_app,
                                                              available_equipment):
    # The Tripod is available when Student A opens the form.
    login(client, STUDENT_A)
    url = f"/catalog/{available_equipment}/reserve"
    assert client.get(url).status_code == 200

    # While that form is open, mark the same Tripod as under maintenance.
    # This simulates a real change between opening the page and clicking Submit.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        connection.execute("UPDATE equipment SET status = 'maintenance' WHERE id = ?",
                           (available_equipment,))

    # Send valid dates and a valid token. The server must use the Tripod's
    # current status when deciding whether to accept the booking.
    response = client.post(url, data={
        "csrf_token": get_token(client), "start_date": "2026-11-17",
        "end_date": "2026-11-20",
    })
    assert response.status_code == 400
    assert b"no longer available" in response.data

    # Verify the outcome in storage, the student saw the error,
    # and no reservation was saved for the Tripod.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM reservations WHERE equipment_id = ?", (available_equipment,),
        ).fetchone()[0] == 0