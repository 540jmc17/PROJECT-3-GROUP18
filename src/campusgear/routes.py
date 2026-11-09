"""
Module Name: routes.py

Description:
    Defines the public website routes and navigation for CampusGear.
    Uses a Flask Blueprint to organize page routes and render the
    corresponding HTML templates.

    These routes support Sprint 1, Requirement #4 (Navigation Menu).
    The catalog and login pages are currently placeholders until
    their respective features are integrated.

Inputs:
    HTTP GET requests to the public website URLs:
        - /
        - /catalog
        - /about
        (/login is provided by presentation/login.py)

Outputs:
    HTML pages rendered through Flask templates, with the active
    navigation page identified using the active_page variable.

Implementation Author: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
Creation Date: 11/6/26.
Reviewed by: Jake Crawford and John Pannell.
Documentation Author: Jake Crawford and John Pannell.
External Sources / Attribution: Flask documentation - Blueprints and Application Routing.
Code Origin: Newly written for EECS 581 Project 3 with assistance from ChatGPT.
Revisions: November 8, 2026 - Ahmed Gharib connected /catalog to the database
    (Requirement #3) using get_catalog(), with code-drafting assistance from
    Claude (Anthropic). Reviewed by Ahmed Gharib.
"""

# Import Blueprint to organize the website's routes.
# Import render_template to display the HTML pages.
from flask import Blueprint, render_template

from .business_logic.equipment_management import get_catalog

# Create a Blueprint named "site" to group our website routes.
# This Blueprint is registered in __init__.py.
site = Blueprint("site", __name__)


# Homepage Route
# Opens the Homepage when users visit the main website URL.
# active_page highlights Home in the navigation menu.
@site.get("/")
def home():
    return render_template("home.html", active_page="home")


# Equipement Catalog Route
# Opens the equipement catalog when users select it from the menu.
# The actual equipement database will be connnected by the catalog team.
@site.get("/catalog")
def catalog():
    # Requirement #3 (Ahmed Gharib): load equipment from the database.
    items = get_catalog()
    available_count = sum(1 for item in items if item["status"] == "available")
    return render_template("catalog.html", active_page="catalog",
                           items=items, available_count=available_count)


# About Page Route
# Displays information about CampusGear and its purpose.
# Highlights About in the navigation menu.
@site.get("/about")
def about():
    return render_template("about.html", active_page="about")


# NOTE: The /login route now lives in presentation/login.py (Requirement #5),
# registered as the "auth" Blueprint. The old navigation-only placeholder
# route was removed to avoid two handlers for the same URL.
