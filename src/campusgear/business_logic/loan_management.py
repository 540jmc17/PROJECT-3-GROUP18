# Name: loan_management.py
# Description: Student Loan Information module of the Business Logic Layer.
#              Retrieves the currently checked-out equipment associated
#              with a student account. The get_active_loans() function
#              queries the loans and equipment tables to retrieve the
#              equipment name, unique asset ID, and expected return date.
#              Results are ordered by due date so students can easily
#              identify which items need to be returned first (Requirement 16).
# Programmer: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
# Dates: November 19, 2026
# Revisions: None
# Preconditions: A Flask application context must be active, and
#                app.config["DATABASE"] must contain the configured database
#                path. The database must contain initialized loans and
#                equipment tables. A valid student ID must be provided.
# Postconditions: Returns the student's currently checked-out equipment,
#                 including the equipment name, asset ID, and due date.
#                 Results are ordered by expected return date. The function
#                 does not modify any database records.
# Errors: Missing application context or database configuration, or database
#         query errors -> Flask or SQLite exceptions.

from flask import current_app

from ..db import transaction


def get_active_loans(student_id):
    """Return currently checked-out equipment, ordered by expected return date."""
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