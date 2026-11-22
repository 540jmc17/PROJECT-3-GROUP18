# Name: login.py
# Description: Login Interface of the Presentation Layer (Requirement 5).
#              Defines the "auth" Blueprint with the /login page (GET shows the
#              form, POST authenticates) and the /logout action. It contains no
#              password or database logic; it calls business_logic.user_access
#              and then redirects by role (students to /student, staff to
#              /staff). Every failure shows the single message
#              "Invalid credentials" so attackers cannot learn which emails
#              exist.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: The Blueprint is registered by create_app(). The form posts
#                the fields email, password and csrf_token. The templates
#                login.html and base.html exist.
# Postconditions: A successful POST leaves a fresh session (user_id, role,
#                 name) and returns a 302 redirect to the role's landing page.
#                 A failed POST returns HTTP 401 and sets no session identity.
#                 /logout always leaves an empty session and redirects to
#                 /login.
# Errors: Bad credentials, unknown emails and blank fields all give HTTP 401
#         with the generic message. A missing or wrong CSRF token gives HTTP
#         400. GET /logout gives HTTP 405 because logout is POST-only.

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)

from ..business_logic.user_access import (authenticate, csrf_is_valid,
                                          current_user, end_session,
                                          home_for_role, start_session)

auth = Blueprint("auth", __name__)

# One generic message for every failure path (prevents account enumeration).
GENERIC_LOGIN_ERROR = "Invalid credentials"


def _render_login(error=None, status=200):
    """Render the login page; `active_page` highlights Sign in in the menu."""
    return render_template("login.html", active_page="login", error=error), status


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form (GET) or authenticate the submitted credentials."""
    if request.method == "GET":
        user = current_user()
        if user is not None:  # already signed in: skip the form
            return redirect(home_for_role(user["role"]))
        return _render_login()

    # --- 1. CSRF check before touching credentials ---------------------------
    if not csrf_is_valid():
        abort(400)

    # --- 2. Verify the credentials (never reveals which part was wrong) -----
    user = authenticate(request.form.get("email", ""),
                        request.form.get("password", ""))
    if user is None:
        return _render_login(GENERIC_LOGIN_ERROR, 401)

    # --- 3. Start a fresh session and redirect by role ----------------------
    # The role comes from the database row, never from the submitted form.
    start_session(user)
    return redirect(home_for_role(user["role"]))


@auth.post("/logout")
def logout():
    """End the session. POST-only + CSRF so another site cannot log you out."""
    if not csrf_is_valid():
        abort(400)
    end_session()  # session.clear(): identity, role and CSRF token removed
    flash("You have been logged out.", "info")  # shown once on the login page
    return redirect(url_for("auth.login"))
