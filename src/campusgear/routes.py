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
"""

# Import Blueprint to organize the website's routes.
# Import render_template to display the HTML pages.
from flask import Blueprint, render_template

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
    # Placeholder until Requirement #3's real database-backed catalog is merged.
    return render_template("catalog.html", active_page="catalog")


# About Page Route
# Displays information about CampusGear and its purpose.
# Highlights About in the navigation menu.
@site.get("/about")
def about():
    return render_template("about.html", active_page="about")


# NOTE: The /login route now lives in presentation/login.py (Requirement #5),
# registered as the "auth" Blueprint. The old navigation-only placeholder
# route was removed to avoid two handlers for the same URL.
