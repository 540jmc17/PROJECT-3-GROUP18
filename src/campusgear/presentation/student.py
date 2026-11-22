"""
Module Name: student.py
Description:
    Student Interface of CampusGear's Presentation Layer. Defines the student
    landing page (Requirement 7), private records page (Requirement 6), active
    loans page (Requirement 16), and reservation forms, list, and cancellation
    action (Requirements 8, 9, 10, 15, and 25).

    Both reservation entry points are preserved: a form for one catalog item
    and a form with an equipment selector. All reservation writes use the
    shared business layer, and all POST handlers validate the CSRF token.
Inputs:
    HTTP requests, authenticated account details, URL identifiers, and form
    fields. The catalog form supplies start_date and end_date; the equipment
    selector supplies equipment_id, pickup_date, and return_date. Both forms
    and the cancellation action require csrf_token.
Outputs:
    Rendered student pages, form errors, and redirects with success or error
    messages. Catalog bookings and cancellations return to the student's
    records page; bookings from the equipment selector return to the list.
Implementation Authors:
    Zema Samuel: original student interface and reservation list/form routes.
    Jake Crawford and John Pannell: catalog reservation form, active loans,
    and reservation confirmation workflow.
Creation Date:
    November 7, 2026: original student interface.
Revisions:
    November 19, 2026: Jake Crawford and John Pannell added Requirements 8,
    16, and 25 with substantial ChatGPT Pro-6 code-drafting assistance.
    November 21, 2026: Zema Samuel added routes for Requirements 9, 10, and 15.
    November 22, 2026: combined the branch implementations, aligned business
    function calls, and standardized documentation with OpenAI Codex.
Review Status:
    Zema Samuel reviewed his original branch implementation.
    The integrated version and revised documentation await team review.
Documentation Attribution:
    Original documentation: Zema Samuel, Jake Crawford, and John Pannell.
    Combined prologue and revised comments/docstrings: OpenAI Codex-assisted.
External Sources / AI Attribution:
    Original student workflow additions credit ChatGPT Pro-6 assistance.
    Integration and documentation revisions were assisted by OpenAI Codex.
    Uses Flask blueprints, Jinja2 templates, SQLite, and existing project helpers.
Code Origin:
    Combined Sprint 1 and Sprint 2 implementations for EECS 581 Project 3.
Preconditions:
    create_app() registers the blueprint and initializes the database.
    The merged reservation_management.py and templates from both branches
    are present. Authentication decorators provide trusted account details.
Postconditions:
    Student-only routes reject staff and unauthenticated access. Private
    records are visible only to their owner or staff. Success messages are
    issued after writes commit, and no password hashes are rendered.
Errors:
    Guests are redirected to login. Unauthorized accounts receive HTTP 403;
    missing records receive HTTP 404. Invalid CSRF tokens and reservation
    submissions receive HTTP 400. Handled creation database errors receive
    HTTP 500. Cancellation errors are shown after a redirect.
"""

from sqlite3 import Error as DatabaseError

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request, url_for,
)

from ..business_logic.loan_management import get_active_loans
from ..business_logic.reservation_management import (
    ReservationError, cancel_reservation, create_reservation,
    get_reservations_for_user, reservation_today,
)
from ..business_logic.user_access import (
    csrf_is_valid, current_user, get_student_records,
    owner_or_staff_required, role_required,
)
from ..config import ROLE_STUDENT
from ..db import get_record, transaction


# Blueprint endpoints use the "student." prefix in templates and redirects.
student_bp = Blueprint("student", __name__)


# ---------------------------------------------------------------------------
# Requirements 6 and 7: Student home and private records
# ---------------------------------------------------------------------------

@student_bp.get("/student")
@role_required(ROLE_STUDENT)
def student_home():
    """Render the student landing page for the authenticated student."""
    return render_template("student_home.html", active_page="student",
                           user=current_user())


@student_bp.get("/students/<int:student_id>/records")
@owner_or_staff_required("student_id")
def student_records(student_id):
    """Render a student's private reservations and loans for the owner or staff.

    Args:
        student_id (int): The student ID supplied by the URL.

    Returns:
        str: The rendered records page after the decorator authorizes access.
    """
    data = get_student_records(student_id)
    if data is None:
        abort(404)

    # Unpack the retrieved student, reservations, and loans into template values.
    return render_template("student_records.html", active_page="student",
                           user=current_user(), **data)


# ---------------------------------------------------------------------------
# Requirement 16: Display active loans and due dates
# ---------------------------------------------------------------------------

@student_bp.get("/student/loans/active")
@role_required(ROLE_STUDENT)
def active_loans():
    """Render active equipment loans and due dates for the signed-in student."""
    # Use the authenticated ID so a URL or form cannot select another borrower.
    loans = get_active_loans(current_user()["id"])
    return render_template("active_loans.html", active_page="student", loans=loans)


# ---------------------------------------------------------------------------
# Requirement 10: Display the student's reservation list
# ---------------------------------------------------------------------------

@student_bp.get("/student/reservations")
@role_required(ROLE_STUDENT)
def student_reservations():
    """Render only reservations belonging to the authenticated student."""
    user = current_user()
    reservations = get_reservations_for_user(user["id"], user["role"])
    return render_template("reservations.html", active_page="student",
                           user=user, reservations=reservations, is_staff=False)


# ---------------------------------------------------------------------------
# Requirements 8, 9, and 25: Reserve an item from the equipment catalog
# ---------------------------------------------------------------------------

@student_bp.route("/catalog/<int:equipment_id>/reserve", methods=["GET", "POST"])
@role_required(ROLE_STUDENT)
def reserve_equipment(equipment_id):
    """Display one item's date form or submit a reservation for that item.

    Args:
        equipment_id (int): The catalog item's ID supplied by the URL.

    Returns:
        str, tuple, or Response: The form, a form with an error status, or a
            redirect to the student's records after a successful booking.
    """
    # Check CSRF before processing a submitted form or looking up the item.
    if request.method == "POST" and not csrf_is_valid():
        abort(400)

    with transaction(current_app.config["DATABASE"]) as connection:
        equipment = get_record(connection, "equipment", equipment_id)
    if equipment is None:
        abort(404)

    student = current_user()
    today = reservation_today()
    form = request.form
    error = None
    status = 200

    if request.method == "POST":
        try:
            # Ownership comes from the session; the business layer rechecks dates
            # and availability when saving. Missing fields become empty strings.
            create_reservation(
                student_id=student["id"], equipment_id=equipment_id,
                start_date=form.get("start_date", ""),
                end_date=form.get("end_date", ""), today=today,
            )
        except ReservationError as exc:
            error, status = str(exc), 400
        except DatabaseError:
            # Log technical details while displaying a general retry message.
            current_app.logger.exception("Could not save reservation")
            error, status = "Could not save your reservation. Please try again.", 500
        else:
            # The transaction has committed. Redirect with GET to avoid resubmission.
            flash("Reservation created successfully.", "success")
            return redirect(url_for("student.student_records", student_id=student["id"]),
                            code=303)
    elif equipment["status"] != "available":
        # Do not offer the initial form for an item that is already unavailable.
        abort(404)

    # Retain submitted values when showing a validation or database error.
    return render_template("reserve_equipment.html", active_page="catalog",
                           equipment=equipment, today=today.isoformat(),
                           form=form, error=error), status


# ---------------------------------------------------------------------------
# Requirements 8, 9, and 25: Reserve an item using the equipment selector
# ---------------------------------------------------------------------------

@student_bp.get("/student/reservations/new")
@role_required(ROLE_STUDENT)
def new_reservation():
    """Render the equipment selector and date fields for a new reservation."""
    with transaction(current_app.config["DATABASE"]) as conn:
        equipment_list = conn.execute(
            "SELECT id, name, asset_id, category FROM equipment "
            "WHERE status = 'available' ORDER BY name"
        ).fetchall()

    # A catalog link may preselect an item; POST validation still checks that item.
    preselected_id = request.args.get("equipment_id", "")
    return render_template(
        "reservation_form.html", active_page="student", user=current_user(),
        equipment_list=[dict(item) for item in equipment_list],
        form={"equipment_id": preselected_id}, error=None,
        today=reservation_today().isoformat(),
    )


@student_bp.post("/student/reservations/new")
@role_required(ROLE_STUDENT)
def create_reservation_route():
    """Save an equipment-selector booking or redisplay the form with an error."""
    if not csrf_is_valid():
        abort(400)

    user = current_user()
    today = reservation_today()
    form = request.form
    equipment_id_raw = form.get("equipment_id", "").strip()
    pickup_date = form.get("pickup_date", "").strip()
    return_date = form.get("return_date", "").strip()
    error = None
    status = 400

    # Reject a missing or nonnumeric selection before calling the business layer.
    try:
        equipment_id = int(equipment_id_raw)
    except (ValueError, TypeError):
        error = "Please select an equipment item."
    else:
        try:
            # Map this form's field names to the merged business function's arguments.
            create_reservation(
                student_id=user["id"], equipment_id=equipment_id,
                start_date=pickup_date, end_date=return_date, today=today,
            )
        except ReservationError as exc:
            error = str(exc)
        except DatabaseError:
            current_app.logger.exception("Could not save reservation")
            error, status = "Could not save your reservation. Please try again.", 500
        else:
            # Confirm only a committed booking, then show the student's reservations.
            flash("Your reservation was created successfully.", "success")
            return redirect(url_for("student.student_reservations"), code=303)

    # Refresh available choices and preserve the submitted fields after a failed POST.
    with transaction(current_app.config["DATABASE"]) as conn:
        equipment_list = conn.execute(
            "SELECT id, name, asset_id, category FROM equipment "
            "WHERE status = 'available' ORDER BY name"
        ).fetchall()
    return render_template(
        "reservation_form.html", active_page="student", user=user,
        equipment_list=[dict(item) for item in equipment_list],
        form=form, error=error, today=today.isoformat(),
    ), status


# ---------------------------------------------------------------------------
# Requirements 15 and 25: Cancel a reservation and display the result
# ---------------------------------------------------------------------------

@student_bp.post("/student/reservations/<int:reservation_id>/cancel")
@role_required(ROLE_STUDENT)
def cancel_student_reservation(reservation_id):
    """Cancel an eligible reservation and redirect to the student's records.

    Args:
        reservation_id (int): The reservation ID supplied by the URL.

    Returns:
        Response: A redirect to the signed-in student's records with feedback.
    """
    if not csrf_is_valid():
        abort(400)

    student_id = current_user()["id"]
    try:
        # Keyword arguments prevent the opposite ID orders in the source branches
        # from being confused. The business layer checks ownership and eligibility.
        cancel_reservation(student_id=student_id, reservation_id=reservation_id)
    except ReservationError as exc:
        flash(str(exc), "error")
    except DatabaseError:
        current_app.logger.exception("Could not cancel reservation")
        flash("Could not cancel your reservation. Please try again.", "error")
    else:
        # The business transaction must succeed before a confirmation is shown.
        flash("Reservation canceled successfully.", "success")

    return redirect(url_for("student.student_records", student_id=student_id), code=303)


# Zema's reservations.html uses this endpoint name; student_records.html uses
# cancel_student_reservation. This alias supports url_for() without registering
# another request handler for the same POST URL.
student_bp.add_url_rule(
    "/student/reservations/<int:reservation_id>/cancel",
    endpoint="cancel_reservation_route", methods=["POST"], build_only=True,
)