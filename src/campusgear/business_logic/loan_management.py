"""
Module Name: loan_management.py
Description: Handles staff checkout from reservations and direct checkout.

Inputs: Checkout form fields and the configured SQLite database.
Outputs: Dropdown choices, saved loans, and updated checkout statuses.

Implementation author: Pranav Reddy, with Codex assistance.
Creation Date: November 19, 2026.
Reviewed by: Pranav Reddy.
Documentation author: Pranav Reddy
External Sources / Attribution: Uses standard Python and SQLite APIs.
Code Origin: Newly written for EECS 581 Project 3, Requirements 11/12.
"""

from datetime import date

from flask import current_app

from ..config import ROLE_STUDENT
from ..db import get_record, insert_record, transaction


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


def checkout_options(): # Helped by Codex
    """Read the dropdown choices for the staff checkout forms."""
    with transaction(current_app.config["DATABASE"]) as connection:
        reservations = connection.execute(
            ELIGIBLE_RESERVATIONS + " ORDER BY r.pickup_date, r.id", (ROLE_STUDENT,)).fetchall()
        students = connection.execute(
            "SELECT id, name, email FROM users WHERE role = ? ORDER BY name, id",
            (ROLE_STUDENT,)).fetchall()
        items = connection.execute(DIRECT_EQUIPMENT + " ORDER BY name, id").fetchall()
    return reservations, students, items


def check_out_equipment(form): # Outline help from Codex
    """Validate the checkout and save the loan and statuses together."""
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
            reservation = connection.execute( # Helped by Codex
                ELIGIBLE_RESERVATIONS + " AND r.id = ?",
                (ROLE_STUDENT, form.get("reservation_id"))).fetchone()
            if reservation is None:
                raise CheckoutError("That reservation is unavailable for checkout.")
            reservation_id = reservation["id"]
            student_id = reservation["user_id"]
            equipment_id = reservation["equipment_id"]
        elif checkout_type == "direct":
            item = connection.execute(DIRECT_EQUIPMENT + " AND id = ?",
                                      (form.get("equipment_id"),)).fetchone() # Helped by Codex
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

        # The transaction rolls back the loan if a status update fails. # Added by Codex
        insert_record(connection, "loans", user_id=student_id, equipment_id=equipment_id,
                      reservation_id=reservation_id, checkout_date=checkout_date, due_date=due_date)
        connection.execute("UPDATE equipment SET status = 'checked_out' WHERE id = ?", (equipment_id,))
        if reservation_id is not None:
            connection.execute("UPDATE reservations SET status = 'checked_out' WHERE id = ?",
                               (reservation_id,))
