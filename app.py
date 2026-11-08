"""
================================================================================
Name:          app.py  (Application Entry Point)
Description:   Builds and configures the CampusGear Flask application. Wires
               the three architectural layers together: registers the Data
               Access Component's lifecycle hooks, exposes the Business Logic
               Layer's role helpers to the templates, and mounts the three
               Presentation Layer blueprints. Also defines the shared error
               pages.

               Supports Sprint 1 Requirement 4 (navigation menu) by making the
               role helpers available to the shared base template that renders
               the menu.

Programmer:    Jake Crawford, John
Created:       11/07/2026
Revisions:     11/07/2026 - Initial version for Sprint 1.

Preconditions: Flask is installed (see requirements.txt). The SECRET_KEY must
               be set to a real random value before this is ever deployed
               outside the course; see config.py.
Postconditions:create_app returns a fully configured Flask application with the
               database file created and the schema applied.
Errors:        sqlite3.OperationalError if the database directory cannot be
               written. Flask raises at startup if two blueprints are
               registered under the same name.

External sources:
  - Claude (Anthropic) assisted with drafting this module and its comments.
  - Application-factory pattern from
    https://flask.palletsprojects.com/en/stable/patterns/appfactories/
================================================================================
"""

from flask import Flask, render_template

import config
from business_logic import access_control, user_access
from data_access import database
from presentation import auth_routes, staff_routes, student_routes


def create_app(test_config=None):
    """
    Build and return a configured Flask application.

    Inputs:  test_config - optional dict of config overrides. The test suite
             passes an in-memory/temporary DATABASE path so tests never touch
             the development database.
    Outputs: A ready-to-run flask.Flask instance.

    Preconditions:  None.
    Postconditions: The database file exists with all tables created, the
                    blueprints are mounted, and the teardown hook is attached.
    Errors:         sqlite3.OperationalError if the database cannot be created.
    """
    app = Flask(__name__)

    # --- Configuration -------------------------------------------------------
    app.config.from_object(config.Config)
    if test_config is not None:
        app.config.update(test_config)

    # --- Data Access Layer ---------------------------------------------------
    # register() attaches close_db to the teardown signal so every request
    # releases its connection; init_db() applies schema.sql.
    database.register(app)
    database.init_db(app)

    # --- Template helpers ----------------------------------------------------
    # Exposed as globals so base.html can decide which navigation links to show
    # without every route having to pass the same three values (Requirement 7).
    app.jinja_env.globals.update(
        is_staff=access_control.is_staff,
        is_student=access_control.is_student,
        is_logged_in=user_access.is_logged_in,
    )

    # Inject the signed-in user into EVERY template render, including the error
    # pages. Without this, base.html's navigation menu raises UndefinedError on
    # a 403 or 404, because the error handlers do not go through a route that
    # passes `user` -- which turned a permission denial into a 500. A route
    # that passes its own `user` still overrides this value, so the explicit
    # arguments in the route functions remain correct.
    register_context_processors(app)

    # --- Presentation Layer --------------------------------------------------
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(student_routes.bp)
    app.register_blueprint(staff_routes.bp)

    # --- Error pages ---------------------------------------------------------
    register_error_handlers(app)

    return app


def register_context_processors(app):
    """
    Make the signed-in user available to every template render.

    Inputs:  app - the Flask application.
    Outputs: None.

    Preconditions:  Called during application construction.
    Postconditions: Every rendered template, including the error pages, can
                    reference `user` without the route having supplied it.
                    When nobody is signed in, `user` is None, which base.html
                    already guards against.
    Errors:         None.

    Why this exists: the navigation menu in base.html renders a link built from
    user['user_id'] for students. The 403 and 404 handlers render that same
    base template but are not reached through a normal route, so they had no
    `user` to pass and Jinja raised UndefinedError -- meaning a student who hit
    a permission denial saw a 500 error instead of the access-denied page. A
    context processor supplies the value centrally, so no handler can forget it.
    """

    @app.context_processor
    def inject_user():
        """Return the template context added to every render.
        Inputs: none. Outputs: dict with `user`. Errors: none."""
        return {"user": user_access.current_user()}


def register_error_handlers(app):
    """
    Attach friendly pages for the HTTP errors this application raises.

    Inputs:  app - the Flask application.
    Outputs: None.

    Preconditions:  Called during application construction.
    Postconditions: 403, 404, and 500 render templates instead of Flask's
                    default white error pages.
    Errors:         None.

    403 matters most here: it is what a student receives when they try to open
    a staff page or another student's records, so it is the visible result of
    Requirement 6 and needs to read as a clear refusal rather than a crash.
    """

    @app.errorhandler(403)
    def forbidden(error):
        """Render the access-denied page. Inputs: the Forbidden exception.
        Outputs: (rendered page, 403). Errors: none."""
        return render_template(
            "error.html",
            code=403,
            title="Access denied",
            message="You do not have permission to view this page.",
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        """Render the not-found page. Inputs: the NotFound exception.
        Outputs: (rendered page, 404). Errors: none."""
        return render_template(
            "error.html",
            code=404,
            title="Page not found",
            message="That page does not exist.",
        ), 404

    @app.errorhandler(500)
    def server_error(error):
        """Render the server-error page. Inputs: the exception.
        Outputs: (rendered page, 500). Errors: none."""
        return render_template(
            "error.html",
            code=500,
            title="Something went wrong",
            message="An unexpected error occurred. Please try again.",
        ), 500


# ==============================================================================
# DEVELOPMENT ENTRY POINT
# `python app.py` runs the built-in server. This is for local development and
# the GTA demo only -- it is not a production server.
# ==============================================================================

if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5000)
