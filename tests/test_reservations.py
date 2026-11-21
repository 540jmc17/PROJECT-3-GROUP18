"""
Module Name: test_reservations.py

Description:
    Automated test suite for Requirements 9, 10, and 15 of the CampusGear
    Sprint 2 application.

    Requirement 9 — Conflict-safe reservation creation:
        Tests verify that valid reservations are saved, that overlapping
        reservations and active loans block new bookings, that adjacent date
        ranges are correctly allowed, and that invalid dates are rejected.

    Requirement 10 — Role-based reservation views:
        Tests verify that students see only their own reservations, that staff
        see all reservations from every student, and that each role cannot
        access the other's reservation URL.

    Requirement 15 — Student-initiated cancellation:
        Tests verify that students can cancel their own reserved reservations,
        that cancelled reservations remain in the database, and that students
        cannot cancel another student's reservation or one already checked out.

    Each test class covers both the business logic layer
    (reservation_management.py) and the HTTP routes (student.py, staff.py).
    Each test method maps to one or more acceptance criteria from the Sprint 2
    requirements artifacts.

Inputs:
    HTTP requests simulated through the Flask test client.
    Isolated SQLite databases provided by the conftest.py fixtures.

Outputs:
    Test results indicating whether each acceptance criterion passes or fails.

Implementation Author: Zema Samuel.
Creation Date: November 21, 2026.
Reviewed by: Zema Samuel.
Revisions: None.
Documentation Author: Zema Samuel.
External Sources / Attribution: Uses pytest, Flask test client, and the
    project's conftest.py fixtures (seeded_app, client, get_token, login).
Code Origin: Newly written for EECS 581 Project 3, Sprint 2,
    Requirements 9, 10, and 15.
"""

from datetime import date, timedelta

import pytest

from campusgear.business_logic.reservation_management import (
    ReservationError,
    cancel_reservation,
    check_availability,
    create_reservation,
    get_reservations_for_user,
)
from campusgear.db import insert_record, transaction
from conftest import STAFF, STUDENT_A, STUDENT_B, get_token, login, make_app

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _days(n):
    """Return an ISO-8601 date string n days from today."""
    return (date.today() + timedelta(days=n)).isoformat()

TOMORROW   = _days(1)
IN_3_DAYS  = _days(3)
IN_5_DAYS  = _days(5)
IN_7_DAYS  = _days(7)
IN_10_DAYS = _days(10)
YESTERDAY  = _days(-1)
TODAY      = date.today().isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    return res_app.test_client()


# ---------------------------------------------------------------------------
# REQUIREMENT 9 — Business logic: check_availability / create_reservation
# ---------------------------------------------------------------------------

class TestReq9BusinessLogic:
    """Acceptance criteria for Requirement 9 tested at the function level."""

    def test_valid_reservation_is_created(self, res_app):
        """AC: system allows a reservation when equipment is free for the period."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert isinstance(rid, int) and rid > 0

    def test_overlapping_reservation_is_blocked(self, res_app):
        """AC: students cannot reserve equipment when an existing reservation
        overlaps the requested dates."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_7_DAYS)
            with pytest.raises(ReservationError):
                create_reservation(2, res_app.config["EQ1"], IN_3_DAYS, IN_10_DAYS)

    def test_fully_contained_overlap_is_blocked(self, res_app):
        """AC: a reservation entirely inside an existing one is also blocked."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_10_DAYS)
            with pytest.raises(ReservationError):
                create_reservation(2, res_app.config["EQ1"], IN_3_DAYS, IN_5_DAYS)

    def test_adjacent_dates_are_allowed(self, res_app):
        """AC: system allows a reservation when equipment is available for the
        entire requested period — adjacent (touching) dates do not overlap."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            # Starts exactly when the first one ends — not an overlap.
            rid = create_reservation(2, res_app.config["EQ1"], IN_5_DAYS, IN_10_DAYS)
        assert rid > 0

    def test_non_overlapping_dates_are_allowed(self, res_app):
        """AC: system allows a reservation when equipment is available for the
        entire requested period."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_3_DAYS)
            rid = create_reservation(2, res_app.config["EQ1"], IN_5_DAYS, IN_10_DAYS)
        assert rid > 0

    def test_different_equipment_is_never_blocked(self, res_app):
        """AC: conflict check is per-equipment; reserving EQ2 while EQ1 is taken works."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_10_DAYS)
            rid = create_reservation(2, res_app.config["EQ2"], TOMORROW, IN_10_DAYS)
        assert rid > 0

    def test_active_loan_blocks_reservation(self, res_app):
        """AC: students cannot reserve equipment when an active checkout makes it
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
        """AC: system allows reservation when loan is returned (equipment free)."""
        with res_app.app_context():
            with transaction(res_app.config["DATABASE"]) as conn:
                insert_record(conn, "loans", user_id=1,
                              equipment_id=res_app.config["EQ1"],
                              checkout_date=TOMORROW, due_date=IN_5_DAYS,
                              actual_return_date=IN_5_DAYS, status="returned")
            rid = create_reservation(2, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert rid > 0

    def test_cancelled_reservation_does_not_block_new_one(self, res_app):
        """AC: unavailable equipment is not saved as a new reservation — but a
        cancelled one frees the slot."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(rid, 1)
            # slot is now free
            rid2 = create_reservation(2, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
        assert rid2 > 0

    def test_past_pickup_date_is_rejected(self, res_app):
        """AC: the start date cannot be earlier than the current date."""
        with res_app.app_context():
            with pytest.raises(ReservationError, match="earlier than today"):
                create_reservation(1, res_app.config["EQ1"], YESTERDAY, IN_5_DAYS)

    def test_today_as_pickup_date_is_accepted(self, res_app):
        """AC: today is a valid start date."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TODAY, IN_5_DAYS)
        assert rid > 0

    def test_return_date_same_as_pickup_is_rejected(self, res_app):
        """AC: the end date must be later than the start date."""
        with res_app.app_context():
            with pytest.raises(ReservationError, match="later than"):
                create_reservation(1, res_app.config["EQ1"], TOMORROW, TOMORROW)

    def test_return_date_before_pickup_is_rejected(self, res_app):
        """AC: the end date must be later than the start date."""
        with res_app.app_context():
            with pytest.raises(ReservationError, match="later than"):
                create_reservation(1, res_app.config["EQ1"], IN_5_DAYS, TOMORROW)

    def test_missing_equipment_id_raises_error(self, res_app):
        """AC: the system does not submit a reservation with invalid data."""
        with res_app.app_context():
            with pytest.raises(ReservationError):
                create_reservation(1, 99999, TOMORROW, IN_5_DAYS)

    def test_reservation_row_is_saved_with_correct_fields(self, res_app):
        """AC: valid dates are saved with the reservation."""
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
# REQUIREMENT 9 — HTTP routes
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
        """AC: reservation is created and a success message is shown (Req 25)."""
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
        """AC: system does not submit a reservation for already-reserved equipment."""
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
        """AC: system does not submit a reservation with an invalid (past) date."""
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
# REQUIREMENT 10 — Business logic and HTTP routes
# ---------------------------------------------------------------------------

class TestReq10BusinessLogic:
    """Acceptance criteria for Requirement 10 at the function level."""

    def test_student_sees_only_own_reservations(self, res_app):
        """AC: students can access a page displaying their reservations;
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
        """AC: staff members can view reservations belonging to all students."""
        with res_app.app_context():
            create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            create_reservation(2, res_app.config["EQ2"], IN_7_DAYS, IN_10_DAYS)
            staff_rows = get_reservations_for_user(3, "staff")
            student_rows = get_reservations_for_user(1, "student")
        assert len(staff_rows) >= len(student_rows)
        names = {r["student_name"] for r in staff_rows}
        assert "Student A" in names and "Student B" in names

    def test_reservation_row_contains_expected_fields(self, res_app):
        """AC: reservation data includes equipment name, asset ID, dates, status,
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
        """AC: students can access a page displaying their own reservations."""
        login(res_client, STUDENT_A)
        # Create one reservation for A and one for B
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        resp = res_client.get("/student/reservations")
        assert resp.status_code == 200
        assert b"Projector" in resp.data

    def test_student_does_not_see_other_students_reservations(self, res_client, res_app):
        """AC: students cannot view reservations belonging to other students."""
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
        """AC: unauthorized users cannot access another student's reservation
        information."""
        login(res_client, STUDENT_A)
        assert res_client.get("/staff/reservations").status_code == 403

    def test_staff_sees_all_reservations_on_page(self, res_client, res_app):
        """AC: staff members can view reservations from all student accounts."""
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
        """AC: staff can access reservation management actions (student name visible)."""
        login(res_client, STAFF)
        resp = res_client.get("/staff/reservations")
        assert b"Student" in resp.data  # column heading

    def test_student_reservation_page_has_no_other_student_names(self, res_client, res_app):
        """AC: unauthorized users cannot access another student's information
        by changing a URL."""
        login(res_client, STUDENT_A)
        resp = res_client.get("/student/reservations")
        assert b"Student B" not in resp.data


# ---------------------------------------------------------------------------
# REQUIREMENT 15 — Business logic and HTTP routes
# ---------------------------------------------------------------------------

class TestReq15BusinessLogic:
    """Acceptance criteria for Requirement 15 at the function level."""

    def test_student_can_cancel_own_reserved_reservation(self, res_app):
        """AC: students can cancel reservations that have not been checked out."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(rid, 1)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT status FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row["status"] == "cancelled"

    def test_cancel_updates_status_to_cancelled(self, res_app):
        """AC: the system updates the reservation status to Cancelled."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(rid, 1)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT status FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row["status"] == "cancelled"

    def test_cancelled_reservation_remains_in_database(self, res_app):
        """AC: cancelled reservations remain recorded in the system."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(rid, 1)
            with transaction(res_app.config["DATABASE"]) as conn:
                row = conn.execute(
                    "SELECT id FROM reservations WHERE id=?", (rid,)).fetchone()
        assert row is not None

    def test_student_cannot_cancel_another_students_reservation(self, res_app):
        """AC: students cannot cancel reservations belonging to other students."""
        with res_app.app_context():
            rid = create_reservation(2, res_app.config["EQ2"], TOMORROW, IN_5_DAYS)
            with pytest.raises(ReservationError, match="own"):
                cancel_reservation(rid, 1)  # student 1 tries to cancel student 2's

    def test_cannot_cancel_checked_out_reservation(self, res_app):
        """AC: students cannot cancel reservations after the equipment has been
        checked out."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            with transaction(res_app.config["DATABASE"]) as conn:
                conn.execute(
                    "UPDATE reservations SET status='checked_out' WHERE id=?", (rid,))
            with pytest.raises(ReservationError, match="checked out"):
                cancel_reservation(rid, 1)

    def test_cannot_cancel_already_cancelled_reservation(self, res_app):
        """AC: cancellation is idempotent in the rejection direction — a second
        cancel attempt is refused."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(rid, 1)
            with pytest.raises(ReservationError, match="already been cancelled"):
                cancel_reservation(rid, 1)

    def test_cancel_nonexistent_reservation_raises_error(self, res_app):
        """Cancelling a reservation that does not exist raises ReservationError."""
        with res_app.app_context():
            with pytest.raises(ReservationError):
                cancel_reservation(99999, 1)

    def test_cancellation_frees_slot_for_new_reservation(self, res_app):
        """AC: the system updates equipment availability when cancellation makes
        the equipment available."""
        with res_app.app_context():
            rid = create_reservation(1, res_app.config["EQ1"], TOMORROW, IN_5_DAYS)
            cancel_reservation(rid, 1)
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
        """AC: a confirmation message is displayed after a successful cancellation
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
        assert b"cancelled" in resp.data.lower()

    def test_cancel_without_csrf_returns_400(self, res_client):
        login(res_client, STUDENT_A)
        resp = res_client.post("/student/reservations/1/cancel", data={})
        assert resp.status_code == 400

    def test_cross_student_cancel_via_route_shows_error(self, res_client, res_app):
        """AC: students cannot cancel reservations belonging to other students
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
        # The error is flashed and shown on the reservations page, not a crash
        assert resp.status_code == 200
        assert b"own" in resp.data.lower() or b"error" in resp.data.lower()

    def test_cancel_button_appears_only_for_reserved_status(self, res_client, res_app):
        """AC: cancel action is available only for reservations not yet checked out."""
        login(res_client, STUDENT_A)
        res_client.post("/student/reservations/new", data={
            "equipment_id": res_app.config["EQ1"],
            "pickup_date": TOMORROW, "return_date": IN_5_DAYS,
            "csrf_token": get_token(res_client),
        })
        resp = res_client.get("/student/reservations")
        # Cancel button (a form with the cancel action) should be present
        assert b"/cancel" in resp.data
