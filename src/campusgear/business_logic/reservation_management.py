"""
Module Name: reservation_management.py

Description:
    Reservation Management component of the Business Logic Layer.
    Implements Requirements 9, 10, and 15 for the CampusGear application.

    Requirement 9 — Prevent reservations for unavailable equipment:
        check_availability() detects date-range conflicts against both the
        reservations and loans tables. create_reservation() validates dates,
        calls check_availability(), and inserts the new row.

    Requirement 10 — Role-based reservation views:
        get_reservations_for_user() returns all reservations for staff and
        only the signed-in student's own reservations for student accounts.

    Requirement 15 — Student-initiated cancellation:
        cancel_reservation() verifies ownership and status before setting
        the reservation status to 'cancelled'.

    All database access uses campusgear.db.transaction(). No raw user input
    is ever interpolated into an SQL string; every variable value is passed
    as a bound parameter (?), preventing SQL injection.

Inputs:
    Function arguments: user IDs, equipment IDs, and date strings in
    YYYY-MM-DD format. Database path is read from Flask's app config.

Outputs:
    Reservation IDs on creation. Lists of reservation dicts for views.
    ReservationError exceptions for all business-rule violations.

Implementation Author: Zema Samuel.
Creation Date: November 21, 2026.
Reviewed by: Zema Samuel.
Revisions: None.
Documentation Author: Zema Samuel.
External Sources / Attribution: Uses Flask, SQLite, and the project's
    existing db.py helpers (transaction, insert_record).
Code Origin: Newly written for EECS 581 Project 3, Sprint 2,
    Requirements 9, 10, and 15.
"""

from datetime import date

from flask import current_app

from ..db import insert_record, transaction

# ---------------------------------------------------------------------------
# Custom exception — mirrors EquipmentError in equipment_management.py so
# callers can catch one known type for all business-rule failures.
# ---------------------------------------------------------------------------

class ReservationError(ValueError):
    """Raised when a reservation action violates a business rule."""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _db_path():
    """Return the shared database path from the Flask app config."""
    return current_app.config["DATABASE"]


def _today_str():
    """Return today's date as a YYYY-MM-DD string."""
    return date.today().isoformat()


def _validate_dates(pickup_date, return_date):
    """Raise ReservationError if the date range is invalid.

    Rules (from Requirement 8 acceptance criteria, enforced here as a guard):
      - Dates must be non-empty strings.
      - pickup_date must not be earlier than today.
      - return_date must be strictly later than pickup_date.
    """
    if not pickup_date or not return_date:
        raise ReservationError("Both a pickup date and a return date are required.")
    today = _today_str()
    if pickup_date < today:
        raise ReservationError(
            "The pickup date cannot be earlier than today.")
    if return_date <= pickup_date:
        raise ReservationError(
            "The return date must be later than the pickup date.")


# ---------------------------------------------------------------------------
# Requirement 9 — Conflict detection
# ---------------------------------------------------------------------------

def check_availability(equipment_id, pickup_date, return_date):
    """Raise ReservationError if the equipment is unavailable for the period.

    Checks both the reservations table and the loans table for any record
    whose date range overlaps the requested period.

    Two date ranges overlap when:
        existing_start < requested_end  AND  existing_end > requested_start

    This is the standard interval-overlap test. It correctly handles all
    partial and full overlaps without special-casing adjacency.

    Reservations with status 'cancelled' or 'completed' do not block new
    reservations. Loans with status 'returned' do not block new reservations.
    """
    with transaction(_db_path()) as conn:
        # Check the reservations table first (Req 9: "already reserved").
        # A reservation that was cancelled or completed no longer holds the
        # equipment, so those statuses are excluded from the conflict check.
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

        # Check the loans table (Req 9: "already checked out").
        # An active loan occupies the equipment from checkout_date through
        # due_date. Returned loans no longer block new reservations.
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
# Requirement 9 — Create reservation
# ---------------------------------------------------------------------------

def create_reservation(user_id, equipment_id, pickup_date, return_date):
    """Validate, check availability, and save a new reservation.

    Validates dates, confirms no conflicts, then inserts a reservation row
    with status 'reserved'. Returns the new reservation's database ID.

    Raises ReservationError for any business-rule violation.

    Args:
        user_id      (int): The signed-in student's user ID.
        equipment_id (int): The equipment item being reserved.
        pickup_date  (str): Requested start date as 'YYYY-MM-DD'.
        return_date  (str): Requested end date as 'YYYY-MM-DD'.

    Returns:
        int: The newly created reservation's primary key.
    """
    # Step 1 — validate the date range (Req 8/9).
    _validate_dates(pickup_date, return_date)

    # Step 2 — confirm the equipment exists and is registered.
    with transaction(_db_path()) as conn:
        equipment = conn.execute(
            "SELECT id, name, status FROM equipment WHERE id = ?",
            (equipment_id,),
        ).fetchone()

    if equipment is None:
        raise ReservationError("The selected equipment was not found.")

    # Step 3 — check for date conflicts (Req 9).
    # check_availability raises ReservationError if unavailable.
    check_availability(equipment_id, pickup_date, return_date)

    # Step 4 — insert the reservation.
    with transaction(_db_path()) as conn:
        reservation_id = insert_record(
            conn,
            "reservations",
            user_id=user_id,
            equipment_id=equipment_id,
            pickup_date=pickup_date,
            return_date=return_date,
            status="reserved",
        )

    return reservation_id


# ---------------------------------------------------------------------------
# Requirement 10 — Role-based reservation views
# ---------------------------------------------------------------------------

def get_reservations_for_user(user_id, role):
    """Return reservation rows filtered by role.

    Students (role='student') see only their own reservations.
    Staff (role='staff') see every reservation in the system.

    Each returned dict contains:
        id, equipment_name, asset_id, pickup_date, return_date,
        status, student_name  (always present; useful for staff view).

    Rows are ordered newest first (pickup_date DESC, then id DESC).

    Args:
        user_id (int): The signed-in user's ID (used only for students).
        role    (str): 'student' or 'staff'.

    Returns:
        list[dict]: Reservation rows as dictionaries.
    """
    with transaction(_db_path()) as conn:
        if role == "staff":
            # Staff see all reservations with the student's name.
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
            # Students see only their own reservations (Req 10).
            # The WHERE clause uses a bound parameter — never a string
            # built from user input — so there is no SQL-injection risk.
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
# Requirement 15 — Cancel reservation
# ---------------------------------------------------------------------------

def cancel_reservation(reservation_id, requesting_user_id):
    """Cancel a student's own reservation if it has not been checked out.

    Business rules (Requirement 15 acceptance criteria):
      - The reservation must exist.
      - The signed-in student must own the reservation.
      - The reservation's current status must be 'reserved'.
        (Already checked-out or cancelled reservations cannot be cancelled.)
      - On success the status is updated to 'cancelled'.

    Args:
        reservation_id      (int): The reservation to cancel.
        requesting_user_id  (int): The signed-in student's user ID.

    Raises:
        ReservationError: If any business rule is violated.
    """
    with transaction(_db_path()) as conn:
        # Fetch the reservation so we can verify ownership and status.
        row = conn.execute(
            "SELECT id, user_id, status FROM reservations WHERE id = ?",
            (reservation_id,),
        ).fetchone()

        if row is None:
            raise ReservationError("Reservation not found.")

        reservation = dict(row)

        # Verify ownership (Req 15: students cannot cancel another
        # student's reservation). Compare as ints; both come from the
        # database or the session, never from user-supplied strings.
        if reservation["user_id"] != requesting_user_id:
            raise ReservationError(
                "You can only cancel your own reservations.")

        # Verify the reservation has not already been checked out or
        # cancelled (Req 15: cannot cancel after checkout).
        if reservation["status"] != "reserved":
            if reservation["status"] == "checked_out":
                raise ReservationError(
                    "This reservation has already been checked out and "
                    "cannot be cancelled.")
            if reservation["status"] == "cancelled":
                raise ReservationError(
                    "This reservation has already been cancelled.")
            raise ReservationError(
                "This reservation cannot be cancelled.")

        # All checks passed — update status to 'cancelled'.
        conn.execute(
            "UPDATE reservations SET status = 'cancelled' WHERE id = ?",
            (reservation_id,),
        )
