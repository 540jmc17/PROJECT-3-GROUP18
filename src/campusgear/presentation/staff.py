# Name: staff.py
# Description: Staff Interface of the Presentation Layer. Defines the "staff"
#              Blueprint with the staff landing page (/staff). It is a
#              placeholder that the Requirement 7 owners will extend with
#              equipment management options. Access is limited to staff by
#              @role_required("staff") (Requirement 6).
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: November 8, 2026 - Ahmed Gharib added the staff-only equipment
#            registration form and handler (/staff/equipment/new, Req 2),
#            with substantial code-drafting assistance from Claude (Anthropic).
#            Reviewed by Ahmed Gharib.
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


# ---------------------------------------------------------------------------
# Requirement 2: Equipment Registration (staff only)
# Author: Ahmed (Mado) Gharib, with substantial code-drafting assistance from Claude (Anthropic). Nov 8, 2026.
# Both the form page (GET) and the save handler (POST) are staff-only.
# ---------------------------------------------------------------------------
from flask import abort, flash, redirect, request, url_for  # noqa: E402

from ..business_logic.equipment_management import (  # noqa: E402
    EquipmentError, register_equipment)
from ..business_logic.user_access import csrf_is_valid  # noqa: E402


@staff_bp.get("/staff/equipment/new")
@role_required(ROLE_STAFF)
def new_equipment():
    """Show the blank equipment registration form."""
    return render_template("register_equipment.html", active_page="staff",
                           user=current_user(), form={}, error=None)


@staff_bp.post("/staff/equipment/new")
@role_required(ROLE_STAFF)
def create_equipment():
    """Validate and save a new equipment item, or re-show the form with an error."""
    if not csrf_is_valid():
        abort(400)
    try:
        register_equipment(request.form)
    except EquipmentError as err:
        return render_template("register_equipment.html", active_page="staff",
                               user=current_user(), form=request.form,
                               error=str(err)), 400
    flash(f"Equipment \"{request.form.get('name', '').strip()}\" was registered.", "success")
    return redirect(url_for("site.catalog"))
