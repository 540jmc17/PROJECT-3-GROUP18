"""
Module Name: reservation_management.py
Description:
    Reservation Management component of CampusGear's Business Logic Layer.
    Validates reservation dates using the KU campus calendar (Requirement 8),
    checks equipment status and date conflicts (Requirement 9), retrieves
    reservations by user role (Requirement 10), and cancels eligible student
    reservations (Requirement 15). Presentation routes handle confirmation
    messages after these operations succeed (Requirement 25).
Inputs:
    Authenticated user IDs and roles, equipment and reservation IDs, and
    date strings in YYYY-MM-DD format. The database path comes from the
    Flask application's DATABASE configuration value.
Outputs:
    The ID of a newly saved reservation, lists of reservation dictionaries,
    or an updated reservation status. Invalid reservation actions raise
    ReservationError.
Implementation Authors:
    Jake Crawford and John Pannell: original student reservation workflow.
    Zema Samuel: original Requirements 9, 10, and 15 implementation.
Creation Dates:
    November 19, 2026: student reservation workflow.
    November 21, 2026: Requirements 9, 10, and 15 implementation.
Revisions:
    November 22, 2026: combined the branch implementations with OpenAI Codex
    assistance; standardized comments and docstrings with OpenAI Codex.
Review Status:
    Zema Samuel reviewed his original branch implementation.
    The integrated version and revised documentation await team review.
Documentation Attribution:
    Original documentation: Jake Crawford, John Pannell, and Zema Samuel.
    Combined prologue and revised comments/docstrings: OpenAI Codex-assisted.
External Sources / AI Attribution:
    The student workflow credits substantial code-drafting assistance from
    ChatGPT Pro-6. Integration and documentation revisions were assisted by
    OpenAI Codex. Uses Python, Flask, SQLite, and the project's db.py helpers
    (get_record, insert_record, and transaction).
Code Origin:
    Combined feature-branch implementations for EECS 581 Project 3, Sprint 2.
Preconditions:
    A Flask application context is active and DATABASE identifies an
    initialized database containing users, equipment, reservations, and loans.
    Callers authenticate users, authorize routes, and supply trusted user IDs
    and roles. Reservation creation receives an existing student's ID.
Postconditions:
    Successful creation saves the borrower, equipment, dates, and default
    'reserved' status. Successful cancellation changes the status to
    'cancelled' without deleting the reservation. Failed writes roll back.
Errors:
    Invalid dates, unavailable equipment, overlapping bookings, or ineligible
    cancellations raise ReservationError. Database errors propagate to the
    caller. SQL values are passed as bound parameters.
"""

from contextlib import nullcontext
from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import current_app

from ..db import get_record, insert_record, transaction


CAMPUS_TIMEZONE = ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# Shared exception and helpers
# ---------------------------------------------------------------------------

class ReservationError(ValueError):
    """Raised when a reservation action violates a business rule."""


def _db_path():
    """Return the database path configured for the current Flask application."""
    return current_app.config["DATABASE"]


def reservation_today():
    """Return today's date in the KU campus timezone, America/Chicago."""
    return datetime.now(CAMPUS_TIMEZONE).date()


def _parse_date(value, label):
    """Parse a date string and require the exact YYYY-MM-DD format.

    Args:
        value (str): The submitted date text.
        label (str): The field name to include in an error message.

    Returns:
        date: The validated calendar date.

    Raises:
        ReservationError: If the value is not a valid YYYY-MM-DD date string.
    """
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ReservationError(f"Enter a valid {label} (YYYY-MM-DD).") from error
    # Reject alternate formats that fromisoformat() may otherwise accept.
    if parsed.isoformat() != value:
        raise ReservationError(f"Enter a valid {label} (YYYY-MM-DD).")
    return parsed


# ---------------------------------------------------------------------------
# Requirement 9: Detect overlapping reservations and loans
# ---------------------------------------------------------------------------

def check_availability(equipment_id, pickup_date, return_date, *, connection=None):
    """Reject a date range that overlaps an existing reservation or active loan.

    Args:
        equipment_id (int): The equipment item to check.
        pickup_date (str): A validated start date in YYYY-MM-DD format.
        return_date (str): A validated end date later than the start date.
        connection (sqlite3.Connection, optional): The caller's open database
            connection. If omitted, this function opens and closes its own.

    Returns:
        None: No blocking reservation or loan overlaps the requested range.

    Raises:
        ReservationError: If a blocking reservation or active loan overlaps.

    Notes:
        Ranges overlap when existing_start < requested_end and
        existing_end > requested_start. Touching endpoints are allowed.
        This function checks date conflicts; create_reservation() also checks
        the equipment's stored status. A standalone check does not reserve it.
    """
    # Reuse the creation transaction so the conflict check and insert stay together.
    # nullcontext() leaves an existing connection under the caller's control.
    context = transaction(_db_path()) if connection is None else nullcontext(connection)
    with context as conn:
        # Cancelled and completed reservations no longer block the requested dates.
        conflict_reservation = conn.execute(
            """
            SELECT id FROM reservations
            WHERE equipment_id = ?
              AND status NOT IN ('cancelled', 'completed')
              AND pickup_date < ?
              AND return_date > ?
            LIMIT 1
            """,
            (equipment_id, return_date, pickup_date),
        ).fetchone()

        if conflict_reservation:
            raise ReservationError(
                "That equipment is already reserved for some or all of the "
                "dates you selected. Please choose different dates or a "
                "different item.")

        # Compare active loans against the same range; returned loans are excluded.
        conflict_loan = conn.execute(
            """
            SELECT id FROM loans
            WHERE equipment_id = ?
              AND status = 'checked_out'
              AND checkout_date < ?
              AND due_date > ?
            LIMIT 1
            """,
            (equipment_id, return_date, pickup_date),
        ).fetchone()

        if conflict_loan:
            raise ReservationError(
                "That equipment is already checked out during some or all of "
                "the dates you selected. Please choose different dates or a "
                "different item.")


# ---------------------------------------------------------------------------
# Requirements 8 and 9: Validate dates and create a reservation
# ---------------------------------------------------------------------------

def create_reservation(student_id, equipment_id, start_date, end_date, *, today=None):
    """Validate and save a reservation for an available equipment item.

    Args:
        student_id (int): The authenticated student's user ID.
        equipment_id (int): The equipment item being reserved.
        start_date (str): The requested pickup date in YYYY-MM-DD format.
        end_date (str): The requested return date in YYYY-MM-DD format.
        today (date, optional): The date used to reject past pickups. Defaults
            to the current KU campus date when the caller does not supply it.

    Returns:
        int: The new reservation's ID, returned after the transaction commits.

    Raises:
        ReservationError: If dates are invalid, equipment is missing or
            unavailable, or an existing reservation or loan overlaps.
    """
    # Use one reference date for validation and require a positive borrowing period.
    if today is None:
        today = reservation_today()
    start = _parse_date(start_date, "start date")
    end = _parse_date(end_date, "end date")
    if start < today:
        raise ReservationError(
            "The start date cannot be in the past. Choose a date no earlier than today.")
    if end <= start:
        raise ReservationError("The end date must be later than the start date.")

    with transaction(current_app.config["DATABASE"]) as connection:
        # Lock before reading so competing writes cannot bypass the availability checks.
        connection.execute("BEGIN IMMEDIATE")
        equipment = get_record(connection, "equipment", equipment_id)
        if equipment is None or equipment["status"] != "available":
            raise ReservationError("This equipment is no longer available.")
        # Check both booking tables using the same connection before saving the row.
        check_availability(equipment_id, start.isoformat(), end.isoformat(),
                           connection=connection)
        # The schema supplies the initial 'reserved' status when it is omitted.
        reservation_id = insert_record(
            connection, "reservations", user_id=student_id,
            equipment_id=equipment_id, pickup_date=start.isoformat(),
            return_date=end.isoformat())

    return reservation_id


# ---------------------------------------------------------------------------
# Requirement 10: Retrieve reservations by user role
# ---------------------------------------------------------------------------

def get_reservations_for_user(user_id, role):
    """Return all reservations for staff or the requesting student's reservations.

    Args:
        user_id (int): The authenticated user's ID, used to filter student rows.
        role (str): The authenticated account's role, 'student' or 'staff'.

    Returns:
        list[dict]: Rows containing id, equipment_name, asset_id, pickup_date,
            return_date, status, and student_name. Rows are sorted by pickup
            date descending, then ID descending.
    """
    with transaction(_db_path()) as conn:
        if role == "staff":
            # Staff need reservations from every student, including borrower names.
            rows = conn.execute(
                """
                SELECT r.id,
                       e.name  AS equipment_name,
                       e.asset_id,
                       r.pickup_date,
                       r.return_date,
                       r.status,
                       u.name  AS student_name
                FROM   reservations r
                JOIN   equipment    e ON e.id = r.equipment_id
                JOIN   users        u ON u.id = r.user_id
                ORDER  BY r.pickup_date DESC, r.id DESC
                """,
            ).fetchall()
        else:
            # Filter by the authenticated student's ID, supplied as a bound value.
            rows = conn.execute(
                """
                SELECT r.id,
                       e.name  AS equipment_name,
                       e.asset_id,
                       r.pickup_date,
                       r.return_date,
                       r.status,
                       u.name  AS student_name
                FROM   reservations r
                JOIN   equipment    e ON e.id = r.equipment_id
                JOIN   users        u ON u.id = r.user_id
                WHERE  r.user_id = ?
                ORDER  BY r.pickup_date DESC, r.id DESC
                """,
                (user_id,),
            ).fetchall()

    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Requirement 15: Cancel an eligible student reservation
# ---------------------------------------------------------------------------

def cancel_reservation(student_id, reservation_id):
    """Cancel an owned reservation that is still reserved and has no linked loan.

    Args:
        student_id (int): The authenticated student's user ID; the first argument.
        reservation_id (int): The reservation to cancel; the second argument.

    Returns:
        None: The reservation's 'cancelled' status has been committed.

    Raises:
        ReservationError: If the reservation is missing, belongs to another
            student, is no longer reserved, or has an associated loan.
    """
    with transaction(_db_path()) as conn:
        # Lock before reading so checkout or another cancellation cannot race this one.
        conn.execute("BEGIN IMMEDIATE")
        # Load the stored owner and status before deciding whether to allow cancellation.
        row = conn.execute(
            "SELECT id, user_id, status FROM reservations WHERE id = ?",
            (reservation_id,),
        ).fetchone()

        if row is None:
            raise ReservationError("This reservation cannot be canceled. Reservation not found.")

        reservation = dict(row)

        # Only the authenticated owner may cancel this reservation.
        if reservation["user_id"] != student_id:
            raise ReservationError(
                "This reservation cannot be canceled. You can only cancel your own reservations.")

        # Explain why checked-out, cancelled, or other non-reserved rows are ineligible.
        if reservation["status"] != "reserved":
            if reservation["status"] == "checked_out":
                raise ReservationError(
                    "This reservation cannot be canceled. It has already been checked out and "
                    "cannot be cancelled.")
            if reservation["status"] == "cancelled":
                raise ReservationError(
                    "This reservation cannot be canceled. It has already been cancelled.")
            raise ReservationError(
                "This reservation cannot be canceled.")

        # Keep ownership and status conditions on the update itself. Any linked loan,
        # including a returned one, means the reservation has already been used.
        result = conn.execute(
            """
            UPDATE reservations
            SET status = 'cancelled'
            WHERE id = ? AND user_id = ? AND status = 'reserved'
              AND NOT EXISTS (
                  SELECT 1 FROM loans WHERE reservation_id = reservations.id
              )
            """,
            (reservation_id, student_id),
        )
        if result.rowcount != 1:
            raise ReservationError("This reservation cannot be canceled.")