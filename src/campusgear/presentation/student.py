# Name: student.py
# Description: Student Interface of the Presentation Layer. Defines the
#              "student" Blueprint with the student landing page (/student)
#              and a student's private records page
#              (/students/<id>/records). The landing page is a placeholder
#              that the Requirement 7 owners will extend with borrowing and
#              reservation options. The records page is protected by
#              @owner_or_staff_required (Requirement 6): a student sees only
#              their own records, staff may open any student's.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: The Blueprint is registered by create_app(); the database has
#                been initialized. The user is signed in (decorators redirect
#                to /login otherwise).
# Postconditions: Only a student (for /student) or the owning student / any
#                 staff member (for the records page) receives a 200 response.
#                 No password hash is rendered.
# Errors: Not signed in -> 302 to /login. Wrong role or another student's id
#         -> 403. A staff request for an id that is not a student -> 404.

from flask import Blueprint, abort, render_template

from ..business_logic.user_access import (current_user, get_student_records,
                                          owner_or_staff_required,
                                          role_required)
from ..config import ROLE_STUDENT

student_bp = Blueprint("student", __name__)


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
