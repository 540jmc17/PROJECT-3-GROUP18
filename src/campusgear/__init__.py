"""
Module Name: __init__.py

Description:
    Creates and configures the CampusGear Flask application.
    Sets the locations of the presentation templates and static files,
    applies optional configuration settings, and registers the website
    routes with the Flask application.

    Requirement #5/#6 integration (Zema Samuel, November 7, 2026): also
    applies the hardened session-cookie settings and secret key, sets the
    shared database path (app.config["DATABASE"]), initializes the database,
    registers the login/student/staff blueprints, and adds security headers
    and error pages.

Inputs:
    test_config (dict, optional): Configuration settings used when
    creating the application, primarily for automated testing.

Outputs:
    Flask application: Returns the configured Flask application
    with the CampusGear website routes registered.

Implementation Author: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
Creation Date: 11/6/26.
Reviewed by: Jake Crawford and John Pannell.
Documentation Author: Jake Crawford and John Pannell.
External Sources / Attribution: Flask documentation - Application Factories.
Code Origin: Newly written for EECS 581 Project 3 with assistance from ChatGPT.
"""

import logging
import os
import secrets

from flask import Flask, render_template, request

from .config import (DB_SCHEMA, MIN_SECRET_KEY_LENGTH, env_flag,
                     session_cookie_settings)
from .db import DEFAULT_PATH, initialize

log = logging.getLogger(__name__)


def create_app(test_config=None):
    """
    Create and configure the CampusGear Flask application.

    Args:
        test_config (dict, optional): Additional application settings
            that can be supplied when running automated tests.

    Returns:
        Flask: The configured CampusGear application.
    """

    # Initialize the Flask application and specify the locations
    # of the HTML templates and static files.
    app = Flask(
        __name__,
        template_folder="presentation/templates",
        static_folder="presentation/static"
    )

    # --- Defaults: hardened session cookie, shared database, feature flags ---
    app.config.update(session_cookie_settings())
    app.config.update(
        SECRET_KEY=os.environ.get("CAMPUSGEAR_SECRET_KEY"),
        # Shared database path (the convention suggested in the Req 1 handoff).
        # Every handler uses transaction(current_app.config["DATABASE"]).
        DATABASE=os.environ.get("CAMPUSGEAR_DB_PATH") or str(DEFAULT_PATH),
        DB_SCHEMA=DB_SCHEMA,
        # Throwaway /test/* routes for Req 5/6; OFF unless explicitly enabled.
        ENABLE_TEST_ROUTES=env_flag("CAMPUSGEAR_ENABLE_TEST_ROUTES", False),
    )

    # Apply optional configuration settings when provided.
    if test_config:
        app.config.update(test_config)

    # --- Secret key: environment value, or a random per-process fallback ----
    # A key from the environment must be long enough to be safe. If none is
    # set, generate a random one so the app still runs for local grading
    # (sessions then reset whenever the server restarts).
    secret = app.config.get("SECRET_KEY")
    if not secret:
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        if not app.config.get("TESTING"):
            log.warning("CAMPUSGEAR_SECRET_KEY is not set; using a random key. "
                        "Logins will reset when the server restarts.")
    elif len(secret) < MIN_SECRET_KEY_LENGTH and not app.config.get("TESTING"):
        raise RuntimeError(
            f"CAMPUSGEAR_SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} "
            "characters. Generate one with: "
            "python -c \"import secrets; print(secrets.token_hex(32))\"")

    # Create any missing tables (safe to repeat; existing rows are kept).
    initialize(app.config["DATABASE"])

    # Import the website routes from the routes module.
    from .routes import site
    from .presentation.login import auth
    from .presentation.student import student_bp
    from .presentation.staff import staff_bp
    from .business_logic.user_access import csrf_token, current_user, home_for_role

    # Register the website blueprints so Flask recognizes their URLs.
    app.register_blueprint(site)
    app.register_blueprint(auth)
    app.register_blueprint(student_bp)
    app.register_blueprint(staff_bp)
    if app.config.get("ENABLE_TEST_ROUTES"):
        from .presentation.auth_test_routes import test_bp
        app.register_blueprint(test_bp)  # throwaway; delete after integration

    # --- Template helpers available on every page ---------------------------
    @app.context_processor
    def inject_account_helpers():
        user = current_user()
        return {
            "current_user": user,                  # None when signed out
            "csrf_token": csrf_token,              # for any POST form
            "account_home_url": home_for_role(user["role"]) if user else None,
        }

    # --- Security headers on every response ---------------------------------
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"  # blocks clickjacking
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; form-action 'self'")
        # Pages can show private data: keep browsers from caching them.
        # (Static CSS/JS is excluded so it can still be cached.)
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    # --- Clean error pages (no internal details are shown) ------------------
    def _error_page(status, title, message):
        return render_template("error.html", active_page="", status=status,
                               title=title, message=message), status

    @app.errorhandler(400)
    def bad_request(_err):
        return _error_page(400, "Bad request",
                           "The form was invalid or expired. Reload the page and try again.")

    @app.errorhandler(403)
    def forbidden(_err):
        return _error_page(403, "Forbidden",
                           "You do not have permission to view this page.")

    @app.errorhandler(404)
    def not_found(_err):
        return _error_page(404, "Not found", "That page does not exist.")

    # Return the configured application for app.py to run.
    return app
