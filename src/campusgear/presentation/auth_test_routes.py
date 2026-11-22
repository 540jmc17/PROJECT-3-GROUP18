# Name: auth_test_routes.py
# Description: THROWAWAY validation routes for Requirements 5 and 6. They let
#              the team confirm each security wall before integration:
#              /test/staff-only (staff check), /test/student/<id>/records
#              (owner-or-staff check) and /test/needs-login (login check).
#              Registered only when ENABLE_TEST_ROUTES is true, which is OFF by
#              default. Delete this file and its registration in
#              __init__.py after integration testing.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: CAMPUSGEAR_ENABLE_TEST_ROUTES=1 (or the ENABLE_TEST_ROUTES
#                config key is true) when the app is created.
# Postconditions: With the flag off these URLs do not exist (404). With it on,
#                 each route returns plain text only to permitted users.
# Errors: Same as the decorators: 302 to /login when signed out, 403 when the
#         role or ownership check fails.

from flask import Blueprint

from ..business_logic.user_access import (login_required,
                                          owner_or_staff_required,
                                          role_required)
from ..config import ROLE_STAFF

test_bp = Blueprint("auth_test", __name__, url_prefix="/test")


@test_bp.get("/staff-only")
@role_required(ROLE_STAFF)
def staff_only():
    """A staff-only function; students must receive 403."""
    return "Staff-only function executed.", 200


@test_bp.get("/student/<int:student_id>/records")
@owner_or_staff_required("student_id")
def student_records_stub(student_id):
    """Stand-in private record; only that student or staff may read it."""
    return f"Private records for student {student_id}.", 200


@test_bp.get("/needs-login")
@login_required
def needs_login():
    """Any signed-in user may view; signed-out users go to the login page."""
    return "Protected page reached.", 200
