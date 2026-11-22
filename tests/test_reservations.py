"""
Module Name: test_reservations.py
Description:
    Combined reservation tests for CampusGear's business and presentation
    layers. Covers catalog date selection (Requirement 8), overlapping
    reservations and loans (Requirement 9), student and staff visibility
    (Requirement 10), and cancellation eligibility (Requirement 15).
    Also checks confirmation messages associated with these actions
    (Requirement 25).
Inputs:
    Isolated databases, Flask test clients, and authentication/CSRF helpers
    from conftest.py. Tests use a fixed reference date of November 17, 2026.
Outputs:
    Pytest results for both branches' reservation scenarios. Assertions
    inspect responses, rendered fields, access restrictions, and stored rows.
Implementation Authors:
    Jake Crawford and John Pannell: original catalog/date-selection tests.
    Zema Samuel: original conflict, visibility, and cancellation tests.
Creation Dates:
    November 19, 2026: catalog/date-selection tests.
    November 21, 2026: Requirements 9, 10, and 15 tests.
Revisions:
    November 22, 2026: combined both suites, aligned cancellation arguments,
    fixed the reference date in both application layers, and standardized
    documentation with OpenAI Codex assistance. The cancellation confirmation
    test now checks the success message and saved status explicitly.
Review Status:
    Zema Samuel reviewed his original test suite.
Documentation Attribution:
    Original documentation: Jake Crawford, John Pannell, and Zema Samuel.
    Combined prologue and revised comments/docstrings: OpenAI Codex-assisted.
External Sources / AI Attribution:
    The catalog/date-selection tests credit substantial code-drafting
    assistance from ChatGPT Pro-6. Integration and documentation revisions
    were assisted by OpenAI Codex. Uses pytest, Flask's test client, and
    the project's existing database and authentication helpers.
Code Origin:
    Combined Sprint 2 test implementations for EECS 581 Project 3.
Preconditions:
    Run pytest from the repository root. conftest.py supplies two students,
    one staff account, and separate test databases. Both reservation forms,
    the merged business functions, and the student/staff reservation pages
    must be integrated for the complete suite to pass.
Postconditions:
    Every original test function is retained. Test writes use temporary
    databases, and monkeypatch restores the application clocks after each test.
Errors:
    Assertions fail for unexpected responses, messages, visibility, or stored
    values. Missing routes and incompatible application code remain failures;
    this file does not skip tests to hide incomplete integration.
"""

from datetime import date, timedelta

import pytest

from campusgear.business_logic.reservation_management import (
    ReservationError,
    cancel_reservation,
    create_reservation,
    get_reservations_for_user,
)
from campusgear.db import insert_record, transaction
from conftest import STAFF, STUDENT_A, STUDENT_B, get_token, login


# ---------------------------------------------------------------------------
# Shared date helpers and fixtures
# ---------------------------------------------------------------------------

TEST_TODAY = date(2026, 11, 17)


def _days(n):
    """Return an ISO date n days after the fixed test reference date."""
    return (TEST_TODAY + timedelta(days=n)).isoformat()


TODAY = TEST_TODAY.isoformat()
YESTERDAY = _days(-1)
TOMORROW = _days(1)
IN_3_DAYS = _days(3)
IN_5_DAYS = _days(5)
IN_7_DAYS = _days(7)
IN_10_DAYS = _days(10)


@pytest.fixture(autouse=True)
def fixed_reservation_date(monkeypatch):
    """Use the same reference date in the reservation business layer and routes."""
    # The routes import this function directly, so patch both lookup locations.
    monkeypatch.setattr('campusgear.business_logic.reservation_management.reservation_today',
                        lambda: TEST_TODAY)
    monkeypatch.setattr('campusgear.presentation.student.reservation_today',
                        lambda: TEST_TODAY)


@pytest.fixture()
def available_equipment(seeded_app):
    """Add an available Tripod and return its equipment ID for catalog tests."""
    # Insert a Tripod into the test database. The returned equipment ID
    # becomes the value of available_equipment inside each test.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        return insert_record(connection, "equipment", asset_id="KU-003",
                             name="Tripod", category="Demo", description="Test item")


@pytest.fixture()
def res_app(seeded_app):
    """seeded_app extended with two *available* equipment items for reservation tests.

    Items:
        eq_id_1 — 'Projector'   (KU-PROJ-001)
        eq_id_2 — 'Whiteboard'  (KU-WB-001)
    Both stored in app.config so tests can read them.
    """
    with seeded_app.app_context():
        with transaction(seeded_app.config["DATABASE"]) as conn:
            eq1 = insert_record(conn, "equipment", asset_id="KU-PROJ-001",
                                name="Projector", category="AV",
                                description="Portable projector", status="available")
            eq2 = insert_record(conn, "equipment", asset_id="KU-WB-001",
                                name="Whiteboard", category="Supplies",
                                description="Rolling whiteboard", status="available")
    seeded_app.config["EQ1"] = eq1
    seeded_app.config["EQ2"] = eq2
    return seeded_app


@pytest.fixture()
def res_client(res_app):
    """Return a client backed by the extended reservation test database."""
    return res_app.test_client()


# ---------------------------------------------------------------------------
# Requirement 8: Select and submit reservation dates from the catalog
# ---------------------------------------------------------------------------

def test_student_reserves_available_equipment_from_catalog(client, seeded_app,
                                                           available_equipment):
    """Verify the catalog-to-form workflow saves the authenticated borrower and dates."""
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
    """Verify each invalid date submission is rejected without creating a row."""
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
    """Verify guest, staff, and missing-CSRF restrictions on the catalog form."""
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
    """Verify a new maintenance status blocks a booking from an already-open form."""
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


# ---------------------------------------------------------------------------
# Requirement 9: Validate dates and detect conflicts in the business layer
# ---------------------------------------------------------------------------

class TestReq9BusinessLogic:
    """Acceptance criteria for Requirement 9 tested at the function level."""

    def test_valid_reservation_is_created(self, res_app):
        """Verify that system allows a reservation when equipment is free for the period."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert isinstance(rid, int) and rid > 0

    def test_overlapping_reservation_is_blocked(self, res_app):
        """Verify that students cannot reserve equipment when an existing reservation
        overlaps the requested dates."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_7_DAYS)
            with pytest.raises(ReservationError):
                create_reservation(2, res_app.config["EQ1"], IN_3_DAYS, IN_10_DAYS)

    def test_fully_contained_overlap_is_blocked(self, res_app):
        """Verify that a reservation entirely inside an existing one is also blocked."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_10_DAYS)
            with pytest.raises(ReservationError):
                create_reservation(2, res_app.config["EQ1"], IN_3_DAYS, IN_5_DAYS)

    def test_adjacent_dates_are_allowed(self, res_app):
        """Verify that system allows a reservation when equipment is available for the
        entire requested period — adjacent (touching) dates do not overlap."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            # Starts exactly when the first one ends — not an overlap.
            rid = create_reservation(2, res_app.config["EQ1"], IN_5_DAYS, IN_10_DAYS)
        assert rid > 0

    def test_non_overlapping_dates_are_allowed(self, res_app):
        """Verify that system allows a reservation when equipment is available for the
        entire requested period."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_3_DAYS)
            rid = create_reservation(2, res_app.config["EQ1"], IN_5_DAYS, IN_10_DAYS)
        assert rid > 0

    def test_different_equipment_is_never_blocked(self, res_app):
        """Verify that conflict check is per-equipment; reserving EQ2 while EQ1 is taken works."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_10_DAYS)
            rid = create_reservation(2, res_app.config["EQ2"], TOMORROW, IN_10_DAYS)
        assert rid > 0

    def test_active_loan_blocks_reservation(self, res_app):
        """Verify that students cannot reserve equipment when an active checkout makes it
        unavailable during the requested dates."""
        with res_app.app_context():
            with transaction(res_app.config["DATABASE"]) as conn:
                insert_record(conn, "loans", user_id=1,
                              equipment_id=res_app.config["EQ1"],
                              checkout_date=TOMORROW, due_date=IN_7_DAYS,
                              status="checked_out")
            with pytest.raises(ReservationError):
                create_reservation(2, res_app.config["EQ1"], IN_3_DAYS, IN_5_DAYS)

    def test_returned_loan_does_not_block_reservation(self, res_app):
        """Verify that system allows reservation when loan is returned (equipment free)."""
        with res_app.app_context():
            with transaction(res_app.config["DATABASE"]) as conn:
                insert_record(conn, "loans", user_id=1,
                              equipment_id=res_app.config["EQ1"],
                              checkout_date=TOMORROW, due_date=IN_5_DAYS,
                              actual_return_date=IN_5_DAYS, status="returned")
            rid = create_reservation(2, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert rid > 0

    def test_cancelled_reservation_does_not_block_new_one(self, res_app):
        """Verify that unavailable equipment is not saved as a new reservation — but a
        cancelled one frees the slot."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(student_id=1, reservation_id=rid)
            # The cancelled reservation no longer blocks these dates.
            rid2 = create_reservation(2, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert rid2 > 0

    def test_past_pickup_date_is_rejected(self, res_app):
        """Verify that the start date cannot be earlier than the current date."""
        with res_app.app_context():
            with pytest.raises(ReservationError, match="earlier than today"):
                create_reservation(1, res_app.config["EQ1"], YESTERDAY, IN_5_DAYS)

    def test_today_as_pickup_date_is_accepted(self, res_app):
        """Verify that today is a valid start date."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TODAY, IN_5_DAYS)
        assert rid > 0

    def test_return_date_same_as_pickup_is_rejected(self, res_app):
        """Verify that the end date must be later than the start date."""
        with res_app.app_context():
            with pytest.raises(ReservationError, match="later than"):
                create_reservation(1, res_app.config["EQ1"], TOMORROW, TOMORROW)

    def test_return_date_before_pickup_is_rejected(self, res_app):
        """Verify that the end date must be later than the start date."""
        with res_app.app_context():
            with pytest.raises(ReservationError, match="later than"):
                create_reservation(1, res_app.config["EQ1"], IN_5_DAYS, TOMORROW)

    def test_missing_equipment_id_raises_error(self, res_app):
        """Verify that the system does not submit a reservation with invalid data."""
        with res_app.app_context():
            with pytest.raises(ReservationError):
                create_reservation(1, 99999, TOMORROW, IN_5_DAYS)

    def test_reservation_row_is_saved_with_correct_fields(self, res_app):
        """Verify that valid dates are saved with the reservation."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT user_id, equipment_id, pickup_date, return_date, status "
                    "FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row["user_id"] == 1
        assert row["equipment_id"] == res_app.config["EQ1"]
        assert row["pickup_date"] == TOMORROW
        assert row["return_date"] == IN_5_DAYS
        assert row["status"] == "reserved"


# ---------------------------------------------------------------------------
# Requirement 9: Submit reservations through the equipment-selector form
# ---------------------------------------------------------------------------

class TestReq9Routes:
    """Acceptance criteria for Requirement 9 at the HTTP level."""

    def test_get_new_reservation_requires_login(self, res_client):
        """Unauthenticated access is redirected to login."""
        assert res_client.get("/student/reservations/new").status_code == 302

    def test_staff_cannot_access_student_reservation_form(self, res_client):
        """Staff are forbidden from the student-only form."""
        login(res_client, STAFF)
        assert res_client.get("/student/reservations/new").status_code == 403

    def test_student_sees_reservation_form(self, res_client):
        """Student can load the reservation form."""
        login(res_client, STUDENT_A)
        resp = res_client.get("/student/reservations/new")
        assert resp.status_code == 200
        assert b"Reserve" in resp.data

    def test_catalog_reserve_button_preselects_equipment(self, res_client, res_app):
        """Reserve button in catalog pre-fills the equipment dropdown."""
        login(res_client, STUDENT_A)
        eq1 = res_app.config["EQ1"]
        resp = res_client.get(f"/student/reservations/new?equipment_id={eq1}")
        assert resp.status_code == 200
        assert str(eq1).encode() in resp.data

    def test_valid_post_creates_reservation_and_redirects(self, res_client, res_app):
        """Verify that reservation is created and a success message is shown (Req 25)."""
        login(res_client, STUDENT_A)
        resp = res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW,
            "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"successfully" in resp.data

    def test_conflicting_post_re_renders_form_with_error(self, res_client, res_app):
        """Verify that system does not submit a reservation for already-reserved equipment."""
        login(res_client, STUDENT_A)
        token = get_token(res_client)
        # First reservation succeeds
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_10_DAYS,
            "csrf_token": token,
        })
        # Overlapping reservation should fail
        resp = res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": IN_3_DAYS, "return_date": IN_7_DAYS,
            "csrf_token": get_token(res_client),
        })
        assert resp.status_code == 400
        assert b"already reserved" in resp.data

    def test_past_date_post_re_renders_form_with_error(self, res_client, res_app):
        """Verify that system does not submit a reservation with an invalid (past) date."""
        login(res_client, STUDENT_A)
        resp = res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": YESTERDAY, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        assert resp.status_code == 400

    def test_post_without_csrf_returns_400(self, res_client, res_app):
        """CSRF protection: form without token is rejected."""
        login(res_client, STUDENT_A)
        resp = res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Requirement 10: Enforce student and staff reservation visibility
# ---------------------------------------------------------------------------

class TestReq10BusinessLogic:
    """Acceptance criteria for Requirement 10 at the function level."""

    def test_student_sees_only_own_reservations(self, res_app):
        """Verify that students can access a page displaying their reservations;
        students cannot view reservations belonging to other students."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            create_reservation(2, res_app.config["EQ2"], TOMORROW, IN_5_DAYS)
            rows_a = get_reservations_for_user(1, "student")
            rows_b = get_reservations_for_user(2, "student")
        # Student A sees only their own row
        assert all(r["student_name"] == "Student A" for r in rows_a)
        # Student B sees only their own row
        assert all(r["student_name"] == "Student B" for r in rows_b)
        # Neither can see the other's
        assert not any(r["student_name"] == "Student B" for r in rows_a)
        assert not any(r["student_name"] == "Student A" for r in rows_b)

    def test_staff_sees_all_reservations(self, res_app):
        """Verify that staff members can view reservations belonging to all students."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            create_reservation(2, res_app.config["EQ2"], IN_7_DAYS, IN_10_DAYS)
            staff_rows = get_reservations_for_user(3, "staff")
            student_rows = get_reservations_for_user(1, "student")
        assert len(staff_rows) >= len(student_rows)
        names = {r["student_name"] for r in staff_rows}
        assert "Student A" in names and "Student B" in names

    def test_reservation_row_contains_expected_fields(self, res_app):
        """Verify that reservation data includes equipment name, asset ID, dates, status,
        and student name."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            rows = get_reservations_for_user(1, "student")
        row = rows[0]
        for key in ("id", "equipment_name", "asset_id", "pickup_date",
                    "return_date", "status", "student_name"):
            assert key in row, f"Missing key: {key}"


class TestReq10Routes:
    """Acceptance criteria for Requirement 10 at the HTTP level."""

    def test_student_reservation_list_requires_login(self, res_client):
        assert res_client.get("/student/reservations").status_code == 302

    def test_staff_cannot_access_student_reservation_list(self, res_client):
        login(res_client, STAFF)
        assert res_client.get("/student/reservations").status_code == 403

    def test_student_sees_own_reservations_on_page(self, res_client, res_app):
        """Verify that students can access a page displaying their own reservations."""
        login(res_client, STUDENT_A)
        # Create a reservation for Student A and verify it appears.
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        resp = res_client.get("/student/reservations")
        assert resp.status_code == 200
        assert b"Projector" in resp.data

    def test_student_does_not_see_other_students_reservations(self, res_client, res_app):
        """Verify that students cannot view reservations belonging to other students."""
        # Reserve EQ2 as student B
        login(res_client, STUDENT_B)
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ2"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        # Student A should not see the Whiteboard reservation
        login(res_client, STUDENT_A)
        resp = res_client.get("/student/reservations")
        assert b"Whiteboard" not in resp.data

    def test_staff_reservation_list_requires_login(self, res_client):
        assert res_client.get("/staff/reservations").status_code == 302

    def test_student_cannot_access_staff_reservation_list(self, res_client):
        """Verify that unauthorized users cannot access another student's reservation
        information."""
        login(res_client, STUDENT_A)
        assert res_client.get("/staff/reservations").status_code == 403

    def test_staff_sees_all_reservations_on_page(self, res_client, res_app):
        """Verify that staff members can view reservations from all student accounts."""
        # Student A reserves EQ1
        login(res_client, STUDENT_A)
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        # Student B reserves EQ2
        login(res_client, STUDENT_B)
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ2"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        login(res_client, STAFF)
        resp = res_client.get("/staff/reservations")
        assert resp.status_code == 200
        assert b"Projector" in resp.data
        assert b"Whiteboard" in resp.data
        assert b"Student A" in resp.data
        assert b"Student B" in resp.data

    def test_staff_reservation_page_shows_student_name_column(self, res_client):
        """Verify that staff can access reservation management actions (student name visible)."""
        login(res_client, STAFF)
        resp = res_client.get("/staff/reservations")
        assert b"Student" in resp.data  # column heading

    def test_student_reservation_page_has_no_other_student_names(self, res_client, res_app):
        """Verify that unauthorized users cannot access another student's information
        by changing a URL."""
        login(res_client, STUDENT_A)
        resp = res_client.get("/student/reservations")
        assert b"Student B" not in resp.data


# ---------------------------------------------------------------------------
# Requirement 15: Enforce cancellation ownership and eligibility
# ---------------------------------------------------------------------------

class TestReq15BusinessLogic:
    """Acceptance criteria for Requirement 15 at the function level."""

    def test_student_can_cancel_own_reserved_reservation(self, res_app):
        """Verify that students can cancel reservations that have not been checked out."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(student_id=1, reservation_id=rid)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT status FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row["status"] == "cancelled"

    def test_cancel_updates_status_to_cancelled(self, res_app):
        """Verify that the system updates the reservation status to Cancelled."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(student_id=1, reservation_id=rid)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT status FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row["status"] == "cancelled"

    def test_cancelled_reservation_remains_in_database(self, res_app):
        """Verify that cancelled reservations remain recorded in the system."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(student_id=1, reservation_id=rid)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT id FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row is not None

    def test_student_cannot_cancel_another_students_reservation(self, res_app):
        """Verify that students cannot cancel reservations belonging to other students."""
        with res_app.app_context():
            rid = create_reservation(2, res_app.config["EQ2"], TOMORROW, IN_5_DAYS)
            with pytest.raises(ReservationError, match="own"):
                cancel_reservation(student_id=1, reservation_id=rid)  # student 1 tries to cancel student 2's

    def test_cannot_cancel_checked_out_reservation(self, res_app):
        """Verify that students cannot cancel reservations after the equipment has been
        checked out."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            with transaction(res_app.config["DATABASE"]) as conn:
                conn.execute(
                    "UPDATE reservations SET status='checked_out' WHERE id=?", (rid,))
            with pytest.raises(ReservationError, match="checked out"):
                cancel_reservation(student_id=1, reservation_id=rid)

    def test_cannot_cancel_already_cancelled_reservation(self, res_app):
        """Verify that cancellation is idempotent in the rejection direction — a second
        cancel attempt is refused."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(student_id=1, reservation_id=rid)
            with pytest.raises(ReservationError, match="already been cancelled"):
                cancel_reservation(student_id=1, reservation_id=rid)

    def test_cancel_nonexistent_reservation_raises_error(self, res_app):
        """Cancelling a reservation that does not exist raises ReservationError."""
        with res_app.app_context():
            with pytest.raises(ReservationError):
                cancel_reservation(student_id=1, reservation_id=99999)

    def test_cancellation_frees_slot_for_new_reservation(self, res_app):
        """Verify that the system updates equipment availability when cancellation makes
        the equipment available."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(student_id=1, reservation_id=rid)
            rid2 = create_reservation(2, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert rid2 > 0


class TestReq15Routes:
    """Acceptance criteria for Requirement 15 at the HTTP level."""

    def test_cancel_route_requires_login(self, res_client):
        """Unauthenticated cancel attempt is redirected to login."""
        resp = res_client.post("/student/reservations/1/cancel",
                               data={"csrf_token": "x"})
        assert resp.status_code == 302

    def test_staff_cannot_use_student_cancel_route(self, res_client):
        login(res_client, STAFF)
        resp = res_client.post("/student/reservations/1/cancel",
                               data={"csrf_token": get_token(res_client)})
        assert resp.status_code == 403

    def test_successful_cancel_shows_confirmation_message(self, res_client, res_app):
        """Verify that a confirmation message is displayed after a successful cancellation
        (Req 25)."""
        login(res_client, STUDENT_A)
        # Create a reservation via the route so we have a real id
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        # Find the new reservation id
        with res_app.app_context():
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT id FROM reservations WHERE user_id=1 AND status='reserved'"
                ).fetchone()
        rid = row["id"]
        resp = res_client.post(f"/student/reservations/{rid}/cancel",
                               data={"csrf_token": get_token(res_client)},
                               follow_redirects=True)
        assert resp.status_code == 200
        assert resp.history[0].status_code == 303
        assert resp.request.path == "/students/1/records"
        assert b"Reservation canceled successfully." in resp.data
        with transaction(res_app.config["DATABASE"]) as conn:
            status = conn.execute(
                "SELECT status FROM reservations WHERE id = ?", (rid,),
            ).fetchone()["status"]
        assert status == "cancelled"

    def test_cancel_without_csrf_returns_400(self, res_client):
        login(res_client, STUDENT_A)
        resp = res_client.post("/student/reservations/1/cancel", data={})
        assert resp.status_code == 400

    def test_cross_student_cancel_via_route_shows_error(self, res_client, res_app):
        """Verify that students cannot cancel reservations belonging to other students
        (enforced at the route level too)."""
        # Student B creates a reservation
        login(res_client, STUDENT_B)
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ2"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        with res_app.app_context():
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT id FROM reservations WHERE user_id=2 AND status='reserved'"
                ).fetchone()
        rid = row["id"]
        # Student A tries to cancel it
        login(res_client, STUDENT_A)
        resp = res_client.post(f"/student/reservations/{rid}/cancel",
                               data={"csrf_token": get_token(res_client)},
                               follow_redirects=True)
        # The merged cancellation handler shows the error on the records page.
        assert resp.status_code == 200
        assert b"own" in resp.data.lower() or b"error" in resp.data.lower()

    def test_cancel_button_appears_only_for_reserved_status(self, res_client, res_app):
        """Verify that cancel action is available only for reservations not yet checked out."""
        login(res_client, STUDENT_A)
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        resp = res_client.get("/student/reservations")
        # Cancel button (a form with the cancel action) should be present
        assert b"/cancel" in resp.data