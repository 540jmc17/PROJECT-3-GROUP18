"""
Module Name: loan_management.py
Description:
    Loan Management component of CampusGear's Business Logic Layer. Handles
    checkout from a reservation (Requirement 11), direct checkout without a
    reservation (Requirement 12), equipment returns (Requirement 13), and
    retrieval of active student loans and due dates (Requirement 16),
    student borrowing history (Requirement 26), and the details used in the
    staff return confirmation message (Requirement 29).
Inputs:
    Checkout and return form fields, authenticated student IDs for loan
    retrieval, and the Flask application's DATABASE configuration value.
Outputs:
    Staff form choices, saved loan records, updated equipment/reservation
    statuses, a student's active equipment loans ordered by due date, a
    student's full borrowing history, and confirmation details for a return.
Implementation Authors:
    Pranav Reddy: staff checkout and returns, with OpenAI Codex assistance.
    Jake Crawford and John Pannell: active-loan and due-date retrieval, with
    substantial ChatGPT Pro-6 code-drafting assistance.
Creation Date:
    November 19, 2026: original checkout and active-loan implementations.
Revisions:
    November 20, 2026: Requirement 13 returns added with OpenAI Codex assistance.
    November 22, 2026: combined staff and student loan functionality and
    standardized comments and docstrings with OpenAI Codex assistance.
    November 22, 2026: Karim Lakhani and Ahmed Gharib added Requirement 26
    (get_borrowing_history) and Requirement 29 (return_equipment now returns
    the saved equipment name and return date) with Claude assistance.
Review Status:
    Pranav Reddy reviewed the original staff implementation.
    The integrated version and revised documentation await team review.
Documentation Attribution:
    Original documentation: Pranav Reddy, Jake Crawford, and John Pannell.
External Sources / AI Attribution:
    Original staff functionality credits OpenAI Codex; the student component
    credits ChatGPT Pro-6. Integration and documentation revisions were
    assisted by OpenAI Codex. Uses Python, Flask, SQLite, and existing project
    database helpers (get_record, insert_record, and transaction).
Code Origin:
    Combined Sprint 2 implementations for EECS 581 Project 3.
Preconditions:
    A Flask application context is active and DATABASE identifies an
    initialized database with users, equipment, reservations, and loans.
    Presentation routes enforce staff access and CSRF checks for writes.
    Student loan retrieval receives the authenticated student's ID.
Postconditions:
    Checkout saves a loan and marks the item and any linked reservation as
    'checked_out'. Return marks the loan 'returned', records the return date,
    updates item condition/availability, and completes a linked reservation
    when its status is 'checked_out'. Related writes commit or roll back
    together. Active-loan and borrowing-history retrieval read records
    without modifying them.
Errors:
    Invalid or ineligible checkouts raise CheckoutError. Invalid or ineligible
    returns raise ReturnError. Configuration and database errors propagate to
    callers. SQL values are supplied as bound parameters.
"""

from datetime import date

from flask import current_app

from ..config import ROLE_STUDENT
from ..db import get_record, insert_record, transaction


# ---------------------------------------------------------------------------
# Shared exceptions and form-choice queries
# ---------------------------------------------------------------------------

class CheckoutError(ValueError):
    """A checkout could not be completed with the submitted details."""


# The dropdown and submission use the same eligibility queries.
ELIGIBLE_RESERVATIONS = """
    SELECT r.id, r.user_id, r.equipment_id, r.pickup_date, r.return_date,
           u.name AS student_name, e.name AS equipment_name, e.asset_id
    FROM reservations AS r
    JOIN users AS u ON u.id = r.user_id
    JOIN equipment AS e ON e.id = r.equipment_id
    WHERE r.status = 'reserved' AND e.status IN ('available', 'reserved') AND u.role = ?
"""

# An outstanding reservation, including a future booking, blocks direct checkout.
DIRECT_EQUIPMENT = """
    SELECT id, name, asset_id FROM equipment
    WHERE status = 'available' AND NOT EXISTS (
        SELECT 1 FROM reservations
        WHERE equipment_id = equipment.id AND status = 'reserved'
    )
"""


# ---------------------------------------------------------------------------
# Requirements 11 and 12: Staff checkout
# ---------------------------------------------------------------------------

def checkout_options():
    """Retrieve reservation, student, and item choices for staff checkout.

    Returns:
        tuple: Three lists of SQLite rows: eligible reservations, student
            accounts, and equipment eligible for direct checkout.
    """
    with transaction(current_app.config["DATABASE"]) as connection:
        reservations = connection.execute(
            ELIGIBLE_RESERVATIONS + " ORDER BY r.pickup_date, r.id", (ROLE_STUDENT,)).fetchall()
        students = connection.execute(
            "SELECT id, name, email FROM users WHERE role = ? ORDER BY name, id",
            (ROLE_STUDENT,)).fetchall()
        items = connection.execute(DIRECT_EQUIPMENT + " ORDER BY name, id").fetchall()
    return reservations, students, items


def check_out_equipment(form):
    """Validate a checkout and save the loan and related statuses together.

    Args:
        form (Mapping): checkout_type, checkout_date, and due_date, plus
            reservation_id for a reservation checkout or equipment_id and
            student_id for a direct checkout. Dates use YYYY-MM-DD format.

    Returns:
        None: The loan and status changes have been committed.

    Raises:
        CheckoutError: If dates, checkout type, selected records, or current
            eligibility are invalid, or a duplicate checkout is attempted.
    """
    checkout_date = form.get("checkout_date", "")
    due_date = form.get("due_date", "")
    try:
        checkout = date.fromisoformat(checkout_date)
        due = date.fromisoformat(due_date)
    except ValueError as err:
        raise CheckoutError("Enter a valid checkout date and expected return date.") from err
    # Match the exact YYYY-MM-DD format required by the database.
    if checkout.isoformat() != checkout_date or due.isoformat() != due_date:
        raise CheckoutError("Use YYYY-MM-DD for both dates.")

    if due <= checkout:
        raise CheckoutError("Expected return date must be after checkout date.")

    # Direct checkout stores a NULL reservation ID on the loan.
    reservation_id = None
    checkout_type = form.get("checkout_type")
    with transaction(current_app.config["DATABASE"]) as connection:
        # Lock before reading so two staff checkouts cannot both claim the same item.
        connection.execute("BEGIN IMMEDIATE")
        if checkout_type == "reservation":
            reservation = connection.execute(
                ELIGIBLE_RESERVATIONS + " AND r.id = ?",
                (ROLE_STUDENT, form.get("reservation_id"))).fetchone()
            if reservation is None:
                raise CheckoutError("That reservation is unavailable for checkout.")
            # Use the stored reservation to identify the borrower and equipment.
            reservation_id = reservation["id"]
            student_id = reservation["user_id"]
            equipment_id = reservation["equipment_id"]
        elif checkout_type == "direct":
            item = connection.execute(DIRECT_EQUIPMENT + " AND id = ?",
                                      (form.get("equipment_id"),)).fetchone()
            if item is None:
                raise CheckoutError("Select equipment that is available for direct checkout.")
            student = get_record(connection, "users", form.get("student_id"))

            if student is None or student["role"] != ROLE_STUDENT:
                raise CheckoutError("Select a valid student account.")
            student_id = student["id"]
            equipment_id = item["id"]

        else:
            raise CheckoutError("Select a checkout type.")

        # Block a second active loan for the item or any repeat use of the reservation.
        existing_loan = connection.execute("""
            SELECT 1 FROM loans
            WHERE (equipment_id = ? AND status = 'checked_out') OR reservation_id = ?
        """, (equipment_id, reservation_id)).fetchone()

        if existing_loan:
            raise CheckoutError("This equipment or reservation already has a checkout.")

        # The transaction rolls back the loan if a status update fails.
        insert_record(connection, "loans", user_id=student_id, equipment_id=equipment_id,
                      reservation_id=reservation_id, checkout_date=checkout_date, due_date=due_date)
        connection.execute("UPDATE equipment SET status = 'checked_out' WHERE id = ?", (equipment_id,))
        if reservation_id is not None:
            connection.execute("UPDATE reservations SET status = 'checked_out' WHERE id = ?",
                               (reservation_id,))


# ---------------------------------------------------------------------------
# Requirement 13: Equipment returns
# ---------------------------------------------------------------------------

class ReturnError(ValueError):
    """A return could not be completed with the submitted details."""


# A good return makes the item available; damage or repair needs require maintenance.
RETURN_CONDITIONS = {
    "good": "available",
    "damaged": "maintenance",
    "needs_repair": "maintenance",
}


def return_options():
    """Retrieve active loans for the staff return form.

    Returns:
        list: SQLite rows containing the loan ID, checkout and due dates,
            borrower name, equipment name, and asset ID, ordered by due date.
    """
    with transaction(current_app.config["DATABASE"]) as connection:
        return connection.execute("""
            SELECT l.id, l.checkout_date, l.due_date, u.name AS student_name,
                   e.name AS equipment_name, e.asset_id
            FROM loans AS l
            JOIN users AS u ON u.id = l.user_id
            JOIN equipment AS e ON e.id = l.equipment_id
            WHERE l.status = 'checked_out' AND l.actual_return_date IS NULL
            ORDER BY l.due_date, l.id
        """).fetchall()


def return_equipment(form):
    """Record a return and update the equipment and linked reservation together.

    Args:
        form (Mapping): loan_id, actual_return_date in YYYY-MM-DD format, and
            condition ('good', 'damaged', or 'needs_repair').

    Returns:
        dict: equipment_name, asset_id, and return_date for the saved return.
            The values come from the database, not the form, and are returned
            only after the transaction commits (used by Requirement 29).

    Raises:
        ReturnError: If the date or condition is invalid, the loan is not an
            active checkout, or the return date precedes the checkout date.
    """
    return_date = form.get("actual_return_date", "")
    try:
        returned = date.fromisoformat(return_date)
    except ValueError as err:
        raise ReturnError("Enter a valid return date in YYYY-MM-DD format.") from err
    if returned.isoformat() != return_date:
        raise ReturnError("Use YYYY-MM-DD for the return date.")

    condition = form.get("condition", "")
    if condition not in RETURN_CONDITIONS:
        raise ReturnError("Select the equipment condition.")

    with transaction(current_app.config["DATABASE"]) as connection:
        # Lock before reading so a repeat or competing return cannot save twice.
        connection.execute("BEGIN IMMEDIATE")
        # Join the equipment so the confirmation names the item on the saved loan.
        loan = connection.execute("""
            SELECT l.id, l.equipment_id, l.reservation_id, l.checkout_date,
                   e.name AS equipment_name, e.asset_id
            FROM loans AS l
            JOIN equipment AS e ON e.id = l.equipment_id
            WHERE l.id = ? AND l.status = 'checked_out' AND l.actual_return_date IS NULL
        """, (form.get("loan_id"),)).fetchone()
        if loan is None:
            raise ReturnError("Select an active loan that has not already been returned.")
        if return_date < loan["checkout_date"]:
            raise ReturnError("Return date cannot be before the checkout date.")

        connection.execute("""
            UPDATE loans SET actual_return_date = ?, status = 'returned' WHERE id = ?
        """, (return_date, loan["id"]))
        # Derive the equipment from the saved loan, never from a submitted item ID.
        connection.execute("UPDATE equipment SET condition = ?, status = ? WHERE id = ?",
                           (condition, RETURN_CONDITIONS[condition], loan["equipment_id"]))
        # Complete a checked-out reservation when its linked loan is returned.
        if loan["reservation_id"] is not None:
            connection.execute("""
                UPDATE reservations SET status = 'completed'
                WHERE id = ? AND status = 'checked_out'
            """, (loan["reservation_id"],))

    # Requirement 29: reaching this line means the transaction committed, so
    # the caller can safely confirm the return. A failure above raises instead.
    return {"equipment_name": loan["equipment_name"], "asset_id": loan["asset_id"],
            "return_date": return_date}


# ---------------------------------------------------------------------------
# Requirement 16: Student active loans and due dates
# ---------------------------------------------------------------------------

def get_active_loans(student_id):
    """Retrieve a student's currently checked-out equipment, ordered by due date.

    Args:
        student_id (int): The authenticated student's user ID.

    Returns:
        list: SQLite rows containing equipment_name, asset_id, and due_date.
            Rows are ordered by due date and then loan ID; returned loans
            are excluded. No records are modified.
    """
    with transaction(current_app.config["DATABASE"]) as connection:
        # The loan supplies the due date. The equipment join supplies its name
        # and asset ID so students can distinguish items with the same name.
        return connection.execute(
            """
            SELECT e.name AS equipment_name, e.asset_id, l.due_date
            FROM loans AS l
            JOIN equipment AS e ON e.id = l.equipment_id
            WHERE l.user_id = ? AND l.status = 'checked_out'
            ORDER BY l.due_date, l.id
            """,
            (student_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# Requirement 26: Student borrowing history
# ---------------------------------------------------------------------------

def get_borrowing_history(student_id):
    """Retrieve every loan a student has had, newest checkout first.

    Args:
        student_id (int): The authenticated student's user ID.

    Returns:
        list: SQLite rows containing equipment_name, asset_id, checkout_date,
            due_date, actual_return_date, and status. Returned loans carry
            their return date; active loans keep actual_return_date as NULL
            and status 'checked_out', so they are never shown as returned.
            No records are modified.
    """
    with transaction(current_app.config["DATABASE"]) as connection:
        # Filter by the borrower on the loan itself, so only this student's
        # records are read. The equipment join supplies the item name.
        return connection.execute(
            """
            SELECT e.name AS equipment_name, e.asset_id, l.checkout_date,
                   l.due_date, l.actual_return_date, l.status
            FROM loans AS l
            JOIN equipment AS e ON e.id = l.equipment_id
            WHERE l.user_id = ?
            ORDER BY l.checkout_date DESC, l.id DESC
            """,
            (student_id,),
        ).fetchall()
