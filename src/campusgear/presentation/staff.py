"""
Module Name: staff.py
Description: Defines the staff home, equipment registration, checkout, and return routes.

Inputs: Staff requests, session details, and submitted form fields.
Outputs: Staff pages, validation errors, and redirects.

Implementation authors: Zema Samuel (staff interface), Ahmed (Mado) Gharib
(equipment registration, with substantial code-drafting assistance from Claude
(Anthropic)), and Codex (full staff checkout implementation for Pranav Reddy).
Creation Date: November 7, 2026.
Revisions: November 8, 2026 (registration). November 19, 2026 (checkout).
Reviewed by: Ahmed Gharib (registration) and Pranav Reddy (checkout).
Documentation author: Pranav Reddy (checkout revision).
External Sources / Attribution: Uses Flask and existing project helpers.
Code Origin: EECS 581 Project 3, Requirements 2, 6, 7, 11/12, and 13.
Req 13 revision: November 20, 2026, implemented with OpenAI Codex assistance.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..business_logic.equipment_management import EquipmentError, register_equipment
from ..business_logic.loan_management import (CheckoutError, ReturnError, RETURN_CONDITIONS,
                                             check_out_equipment, checkout_options,
                                             return_equipment, return_options)
from ..business_logic.user_access import csrf_is_valid, current_user, role_required
from ..config import ROLE_STAFF

staff_bp = Blueprint("staff", __name__)


@staff_bp.get("/staff")
@role_required(ROLE_STAFF)
def staff_home():
    """Show the staff landing page after login."""
    return render_template("staff_home.html", active_page="staff",
                           user=current_user())


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


@staff_bp.route("/staff/checkout", methods=["GET", "POST"])
@role_required(ROLE_STAFF)
def checkout():
    """Show both staff checkout forms and process the submitted form."""
    error = None
    if request.method == "POST":
        if not csrf_is_valid():
            abort(400)
        try:
            check_out_equipment(request.form)
        except CheckoutError as err:
            error = str(err)
        else:
            # Redirect after saving so refreshing the page does not submit twice.
            flash("Equipment checked out.", "success")
            return redirect(url_for("staff.checkout"))

    reservations, students, items = checkout_options()
    page = render_template("checkout.html", active_page="staff", error=error,
                           reservations=reservations, students=students, items=items)
    return page, 400 if error else 200


@staff_bp.route("/staff/returns", methods=["GET", "POST"])
@role_required(ROLE_STAFF)
def returns():
    """Show active loans and process a staff equipment return."""
    error = None
    if request.method == "POST":
        if not csrf_is_valid():
            abort(400)
        try:
            return_equipment(request.form)
        except ReturnError as err:
            error = str(err)
        else:
            flash("Equipment return recorded.", "success")
            return redirect(url_for("staff.returns"))

    page = render_template("returns.html", active_page="staff", error=error,
                           loans=return_options(), conditions=RETURN_CONDITIONS,
                           form=request.form if request.method == "POST" else {})
    return page, 400 if error else 200
