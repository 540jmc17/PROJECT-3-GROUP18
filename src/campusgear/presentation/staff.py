# Name: staff.py
# Description: Staff Interface of the Presentation Layer. Defines the "staff"
#              Blueprint with the staff landing page (/staff). It is a
#              placeholder that the Requirement 7 owners will extend with
#              equipment management options. Access is limited to staff by
#              @role_required("staff") (Requirement 6).
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: The Blueprint is registered by create_app(). The user is
#                signed in (the decorator redirects to /login otherwise).
# Postconditions: Only staff receive a 200 response for /staff.
# Errors: Not signed in -> 302 to /login. A student -> 403.

from flask import Blueprint, render_template

from ..business_logic.user_access import current_user, role_required
from ..config import ROLE_STAFF

staff_bp = Blueprint("staff", __name__)


@staff_bp.get("/staff")
@role_required(ROLE_STAFF)
def staff_home():
    """Placeholder Staff Interface; staff land here after login."""
    return render_template("staff_home.html", active_page="staff",
                           user=current_user())
