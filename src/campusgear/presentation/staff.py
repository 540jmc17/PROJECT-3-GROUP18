"""
Module Name: staff.py
Description:
    Staff Interface of CampusGear's Presentation Layer. Defines the staff
    landing page (Requirement 7), equipment registration (Requirement 2),
    reservation list (Requirement 10), reservation and direct checkout
    (Requirements 11 and 12), equipment returns (Requirement 13), and the
    on-screen return confirmation (Requirement 29).

    Staff-role decorators protect every route (Requirement 6). POST handlers
    validate CSRF tokens before delegating writes to the business layer.
Inputs:
    HTTP requests from staff accounts, authenticated session details, and
    equipment registration, checkout, or return form fields with csrf_token.
Outputs:
    Rendered staff pages, validation errors, and redirects with confirmation
    messages after successful equipment registration, checkout, or return.
Implementation Authors:
    Zema Samuel: original staff interface and reservation list.
    Ahmed (Mado) Gharib: equipment registration, with substantial
    code-drafting assistance from Claude (Anthropic).
    OpenAI Codex: original staff checkout implementation for Pranav Reddy.
    Karim Lakhani and Ahmed Gharib: return confirmation message
    (Requirement 29), with Claude (Anthropic) code-drafting assistance.
Creation Date:
    November 7, 2026: original staff interface.
Revisions:
    November 8, 2026: equipment registration added.
    November 19, 2026: staff checkout added.
    November 20, 2026: Requirement 13 returns added with OpenAI Codex assistance.
    November 22, 2026: preserved the reservation-list import and route while
    combining branches; standardized documentation with OpenAI Codex assistance.
    November 22, 2026: Karim Lakhani and Ahmed Gharib made the return
    confirmation name the equipment and return date (Requirement 29).
Review Status:
    Ahmed Gharib reviewed equipment registration; Pranav Reddy reviewed checkout.
Documentation Attribution:
    Pranav Reddy is credited for the original checkout documentation revision.
External Sources / AI Attribution:
    Equipment registration credits Claude (Anthropic). Staff checkout,
    returns, integration, and documentation revisions credit OpenAI Codex.
    Uses Flask, Jinja2 templates, and the project's existing business and
    authentication helpers.
Code Origin:
    Combined Sprint 1 and Sprint 2 implementations for EECS 581 Project 3.
Preconditions:
    create_app() registers the blueprint and initializes the database.
    The merged loan_management.py and reservation_management.py, along with
    the equipment-registration and authentication modules, are available.
    The staff, reservation, checkout, and return templates are present.
Postconditions:
    Authorized staff can view all reservations, register equipment, check out
    equipment, and record returns. Successful writes commit in the business
    layer before confirmation messages are issued. Failed validation displays
    an error without reporting success.
Errors:
    Guests are redirected to login; non-staff accounts receive HTTP 403.
    Invalid CSRF tokens receive HTTP 400. Handled business-rule errors
    redisplay the relevant form with HTTP 400. Database exceptions propagate
    to Flask rather than being reported as successful actions.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..business_logic.equipment_management import EquipmentError, register_equipment
from ..business_logic.loan_management import (
    CheckoutError, ReturnError, RETURN_CONDITIONS,
    check_out_equipment, checkout_options, return_equipment, return_options,
)
from ..business_logic.reservation_management import get_reservations_for_user
from ..business_logic.user_access import csrf_is_valid, current_user, role_required
from ..config import ROLE_STAFF

# Blueprint endpoints use the "staff." prefix in templates and redirects.
staff_bp = Blueprint("staff", __name__)


# ---------------------------------------------------------------------------
# Requirements 6 and 7: Staff access and landing page
# ---------------------------------------------------------------------------


@staff_bp.get("/staff")
@role_required(ROLE_STAFF)
def staff_home():
    """Render the landing page for an authenticated staff member."""
    return render_template("staff_home.html", active_page="staff",
                           user=current_user())


# ---------------------------------------------------------------------------
# Requirement 2: Equipment registration
# ---------------------------------------------------------------------------

@staff_bp.get("/staff/equipment/new")
@role_required(ROLE_STAFF)
def new_equipment():
    """Render the blank equipment registration form for staff."""
    return render_template("register_equipment.html", active_page="staff",
                           user=current_user(), form={}, error=None)


@staff_bp.post("/staff/equipment/new")
@role_required(ROLE_STAFF)
def create_equipment():
    """Register an equipment item or redisplay the submitted form with an error."""
    # Validate CSRF before allowing the business layer to write a new item.
    if not csrf_is_valid():
        abort(400)
    try:
        register_equipment(request.form)
    except EquipmentError as err:
        # Preserve submitted values so staff can correct the rejected fields.
        return render_template("register_equipment.html", active_page="staff",
                               user=current_user(), form=request.form,
                               error=str(err)), 400
    # The business operation succeeded; confirm the saved item and open the catalog.
    flash(f"Equipment \"{request.form.get('name', '').strip()}\" was registered.", "success")
    return redirect(url_for("site.catalog"))


# ---------------------------------------------------------------------------
# Requirement 10: Staff reservation list
# ---------------------------------------------------------------------------

@staff_bp.get("/staff/reservations")
@role_required(ROLE_STAFF)
def staff_reservations():
    """Render every student's reservations for an authorized staff member."""
    # The staff-role decorator authorizes the unfiltered reservation view.
    reservations = get_reservations_for_user(current_user()["id"], "staff")
    # The shared template includes borrower names and omits student-only controls.
    return render_template("reservations.html", active_page="staff",
                           user=current_user(), reservations=reservations,
                           is_staff=True)


# ---------------------------------------------------------------------------
# Requirements 11 and 12: Reservation and direct checkout
# ---------------------------------------------------------------------------

@staff_bp.route("/staff/checkout", methods=["GET", "POST"])
@role_required(ROLE_STAFF)
def checkout():
    """Render both checkout options or process a staff checkout submission."""
    error = None
    if request.method == "POST":
        # Reject an invalid CSRF token before validating or saving the checkout.
        if not csrf_is_valid():
            abort(400)
        try:
            check_out_equipment(request.form)
        except CheckoutError as err:
            error = str(err)
        else:
            # Confirm the committed checkout and redirect to avoid resubmission.
            flash("Equipment checked out.", "success")
            return redirect(url_for("staff.checkout"))

    # Refresh eligible reservations, borrowers, and items for GET or a rejected POST.
    reservations, students, items = checkout_options()
    page = render_template("checkout.html", active_page="staff", error=error,
                           reservations=reservations, students=students, items=items)
    return page, 400 if error else 200


# ---------------------------------------------------------------------------
# Requirement 13: Equipment returns
# ---------------------------------------------------------------------------

@staff_bp.route("/staff/returns", methods=["GET", "POST"])
@role_required(ROLE_STAFF)
def returns():
    """Render active loans or process a staff equipment-return submission."""
    error = None
    if request.method == "POST":
        # The business layer verifies the loan, return date, and item condition.
        if not csrf_is_valid():
            abort(400)
        try:
            saved = return_equipment(request.form)
        except ReturnError as err:
            error = str(err)
        else:
            # Requirement 29: confirm only after the loan and related status
            # updates commit, naming the item and date read back from the database.
            flash(f"Equipment return recorded. {saved['equipment_name']} "
                  f"({saved['asset_id']}) was returned on {saved['return_date']}.",
                  "success")
            return redirect(url_for("staff.returns"))

    # Preserve return form values on errors and refresh the active-loan choices.
    page = render_template("returns.html", active_page="staff", error=error,
                           loans=return_options(), conditions=RETURN_CONDITIONS,
                           form=request.form if request.method == "POST" else {})
    return page, 400 if error else 200