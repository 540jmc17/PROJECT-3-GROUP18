"""
Module Name: student.py

Description:
    Student Interface of the Presentation Layer for the CampusGear application.
    Defines the "student" Flask Blueprint with the following routes:

    Sprint 1 routes (Zema Samuel):
        GET  /student                       — student landing page (Req 7)
        GET  /students/<id>/records         — private records page (Req 6)

    Sprint 2 routes (Zema Samuel):
        GET  /student/reservations          — view own reservations (Req 10)
        GET  /student/reservations/new      — reservation form (Req 9)
        POST /student/reservations/new      — save reservation (Req 9)
        POST /student/reservations/<id>/cancel — cancel reservation (Req 15)

    All POST routes validate the CSRF token before processing any form data.
    Flash messages are shown after successful actions (Req 25).

Inputs:
    HTTP GET and POST requests from authenticated student accounts.
    Session data (user ID, role, name) set by the authentication layer.
    Form fields: equipment_id, pickup_date, return_date, csrf_token.

Outputs:
    Rendered HTML pages for student views and the reservation form.
    Redirects with flash messages after successful reservation creation
    or cancellation. HTTP 400 responses with re-rendered forms on error.

Implementation Author: Zema Samuel.
Creation Date: November 7, 2026.
Reviewed by: Zema Samuel.
Revisions: November 21, 2026 — added reservation list, create, and cancel
    routes for Requirements 9, 10, and 15 (Sprint 2).
Documentation Author: Zema Samuel.
External Sources / Attribution: Uses Flask blueprints, Jinja2 templates,
    and the project's existing user_access and reservation_management modules.
Code Origin: Sprint 1 routes from EECS 581 Project 3, Sprint 1, Requirement 7.
    Sprint 2 routes newly written for Requirements 9, 10, and 15.
"""

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)

from datetime import date

from ..business_logic.reservation_management import (ReservationError,
                                                     cancel_reservation,
                                                     create_reservation,
                                                     get_reservations_for_user)
from ..business_logic.user_access import (csrf_is_valid, current_user,
                                          owner_or_staff_required,
                                          role_required,
                                          get_student_records)
from ..config import ROLE_STUDENT
from ..db import transaction

student_bp = Blueprint("student", __name__)


# ---------------------------------------------------------------------------
# Sprint 1 — existing routes (unchanged)
# ---------------------------------------------------------------------------

@student_bp.get("/student")
@role_required(ROLE_STUDENT)
def student_home():
    """Placeholder Student Interface; students land here after login."""
    return render_template("student_home.html", active_page="student",
                           user=current_user())


@student_bp.get("/students/<int:student_id>/records")
@owner_or_staff_required("student_id")
def student_records(student_id):
    """A student's private reservations and loans (owner or staff only)."""
    data = get_student_records(student_id)
    if data is None:
        abort(404)  # no such student (only reachable by staff)
    return render_template("student_records.html", active_page="student",
                           user=current_user(), **data)


# ---------------------------------------------------------------------------
# Requirement 10 — View own reservations (student)
# ---------------------------------------------------------------------------

@student_bp.get("/student/reservations")
@role_required(ROLE_STUDENT)
def student_reservations():
    """Display the signed-in student's own reservations (Req 10).

    Students are shown only rows where user_id equals their own id.
    The filtering happens in get_reservations_for_user(), which uses a
    bound SQL parameter — not a URL value — so a student cannot see
    another student's reservations by altering the URL.
    """
    user = current_user()
    reservations = get_reservations_for_user(user["id"], user["role"])
    return render_template("reservations.html", active_page="student",
                           user=user, reservations=reservations,
                           is_staff=False)


# ---------------------------------------------------------------------------
# Requirement 9 — Create reservation (student)
# ---------------------------------------------------------------------------

@student_bp.get("/student/reservations/new")
@role_required(ROLE_STUDENT)
def new_reservation():
    """Show the reservation form (Req 9).

    If the catalog passed ?equipment_id=N the equipment selector is
    pre-filled. The form also lists all available equipment so the
    student can pick one manually.
    """
    user = current_user()
    db_path = _db_path()
    with transaction(db_path) as conn:
        equipment_list = conn.execute(
            "SELECT id, name, asset_id, category FROM equipment "
            "WHERE status = 'available' ORDER BY name"
        ).fetchall()
    # Pre-select if the catalog passed an equipment_id query param.
    preselected_id = request.args.get("equipment_id", "")
    return render_template(
        "reservation_form.html",
        active_page="student",
        user=user,
        equipment_list=[dict(e) for e in equipment_list],
        form={"equipment_id": preselected_id},
        error=None,
        today=date.today().isoformat(),
    )


@student_bp.post("/student/reservations/new")
@role_required(ROLE_STUDENT)
def create_reservation_route():
    """Validate and save a new reservation (Req 9).

    On success: flash a confirmation message (Req 25) and redirect to the
    student's reservations list.
    On failure: re-render the form with the error message and previously
    entered values so the student does not have to retype everything.
    """
    if not csrf_is_valid():
        abort(400)

    user = current_user()
    form = request.form

    equipment_id_raw = form.get("equipment_id", "").strip()
    pickup_date = form.get("pickup_date", "").strip()
    return_date = form.get("return_date", "").strip()

    # Convert equipment_id to int; show a friendly error if it's missing.
    try:
        equipment_id = int(equipment_id_raw)
    except (ValueError, TypeError):
        equipment_id = None

    if equipment_id is None:
        db_path = _db_path()
        with transaction(db_path) as conn:
            equipment_list = conn.execute(
                "SELECT id, name, asset_id, category FROM equipment "
                "WHERE status = 'available' ORDER BY name"
            ).fetchall()
        return render_template(
            "reservation_form.html",
            active_page="student",
            user=user,
            equipment_list=[dict(e) for e in equipment_list],
            form=form,
            error="Please select an equipment item.",
            today=date.today().isoformat(),
        ), 400

    try:
        create_reservation(user["id"], equipment_id, pickup_date, return_date)
    except ReservationError as err:
        db_path = _db_path()
        with transaction(db_path) as conn:
            equipment_list = conn.execute(
                "SELECT id, name, asset_id, category FROM equipment "
                "WHERE status = 'available' ORDER BY name"
            ).fetchall()
        return render_template(
            "reservation_form.html",
            active_page="student",
            user=user,
            equipment_list=[dict(e) for e in equipment_list],
            form=form,
            error=str(err),
            today=date.today().isoformat(),
        ), 400

    # Req 25: confirmation message after successful reservation.
    flash("Your reservation was created successfully.", "success")
    return redirect(url_for("student.student_reservations"))


# ---------------------------------------------------------------------------
# Requirement 15 — Cancel reservation (student)
# ---------------------------------------------------------------------------

@student_bp.post("/student/reservations/<int:reservation_id>/cancel")
@role_required(ROLE_STUDENT)
def cancel_reservation_route(reservation_id):
    """Cancel the student's own reservation if it has not been checked out (Req 15).

    Uses cancel_reservation() in the business logic layer, which enforces:
      - The reservation belongs to the signed-in student.
      - The reservation's status is still 'reserved'.

    On success: flash a confirmation message (Req 25) and redirect to the
    student's reservations list.
    On failure: flash an error message and redirect back to the list.
    """
    if not csrf_is_valid():
        abort(400)

    user = current_user()
    try:
        cancel_reservation(reservation_id, user["id"])
        # Req 25: confirmation message after successful cancellation.
        flash("Your reservation was cancelled.", "success")
    except ReservationError as err:
        flash(str(err), "error")

    return redirect(url_for("student.student_reservations"))


# ---------------------------------------------------------------------------
# Private helper (keeps db_path access consistent with rest of module)
# ---------------------------------------------------------------------------

def _db_path():
    from flask import current_app
    return current_app.config["DATABASE"]
