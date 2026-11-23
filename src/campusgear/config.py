# Name: config.py
# Description: Authentication settings for CampusGear (Requirements 5 and 6).
#              Holds DB_SCHEMA, the single mapping of the users table and
#              column names used by the login code, plus role names, session
#              key names, and helpers that build the hardened session-cookie
#              configuration. Nothing here talks to the database.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: Imported by campusgear.create_app() and by the
#                business_logic.user_access module. Optional environment
#                variables: CAMPUSGEAR_SECRET_KEY, CAMPUSGEAR_COOKIE_SECURE,
#                CAMPUSGEAR_ENABLE_TEST_ROUTES (CAMPUSGEAR_DB_PATH is read in
#                __init__.py).
# Postconditions: DB_SCHEMA, role constants and session-key constants are
#                 available. Importing has no side effects.
# Errors: None are raised here. Invalid DB_SCHEMA identifiers are rejected
#         later by user_access._ident() with a RuntimeError.

import os

# =============================================================================
# DATABASE ABSTRACTION  (edit ONLY this block if the users table is renamed)
# =============================================================================
# Pranav and Cameren's schema.sql defines the table below. If they rename the
# table or a column, change the matching VALUE here. The KEYS are the names the
# login code uses internally and must stay as they are.
DB_SCHEMA = {
    "table": "users",
    "columns": {
        "id": "id",                        # primary key of the user row
        "name": "name",                    # display name
        "email": "email",                  # login identifier (unique, NOCASE)
        "password_hash": "password_hash",  # full werkzeug hash string
        "role": "role",                    # 'student' or 'staff'
    },
}

# =============================================================================
# ROLES AND SESSION KEYS  (teammates read these; keep the names stable)
# =============================================================================
ROLE_STUDENT = "student"
ROLE_STAFF = "staff"
VALID_ROLES = (ROLE_STUDENT, ROLE_STAFF)

SESSION_USER_ID_KEY = "user_id"     # int primary key of the signed-in user
SESSION_ROLE_KEY = "role"           # 'student' or 'staff'
SESSION_NAME_KEY = "name"           # display name (for the page header)
SESSION_CSRF_KEY = "_csrf_token"    # internal anti-CSRF token

# Smallest password accepted when an account is created (create_account()).
MIN_PASSWORD_LENGTH = 8

# Shortest acceptable secret key (characters) when one is set in the environment.
MIN_SECRET_KEY_LENGTH = 32


def env_flag(name, default=False):
    """Read a boolean-like environment variable ('1', 'true', 'yes', 'on')."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def session_cookie_settings():
    """Return the hardened session-cookie settings for app.config.update().

    HttpOnly: JavaScript cannot read the cookie.
    SameSite=Lax: the cookie is not sent on cross-site POST requests.
    Secure: sent only over HTTPS. It defaults to OFF so the app works on
    http://127.0.0.1:5000 for local grading; set CAMPUSGEAR_COOKIE_SECURE=1
    when the site is served over HTTPS.
    """
    return {
        "SESSION_COOKIE_NAME": "campusgear_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": env_flag("CAMPUSGEAR_COOKIE_SECURE", False),
        "SESSION_REFRESH_EACH_REQUEST": True,
        "PERMANENT_SESSION_LIFETIME": 30 * 60,  # idle timeout, in seconds
    }
