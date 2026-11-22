# Name: user_access.py
# Description: User and Access Management component of the Business Logic
#              Layer (Requirements 5 and 6). Looks up users, verifies password
#              hashes, creates accounts, manages the signed-in session, issues
#              and checks anti-CSRF tokens, and provides the three access
#              decorators (@login_required, @role_required and
#              @owner_or_staff_required). It also supplies the ownership-
#              filtered read of a student's private reservation and loan
#              records. All database access goes through Pranav and Cameren's
#              campusgear.db.transaction(); user-table names come from
#              config.DB_SCHEMA.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: Used inside a Flask application created by create_app(), which
#                sets SECRET_KEY and app.config["DATABASE"] and has run
#                db.initialize(). Passwords are stored only as hashes produced
#                by werkzeug.security.generate_password_hash.
# Postconditions: authenticate() returns a user dictionary WITHOUT the
#                 password hash, or None. start_session() leaves a fresh
#                 session holding user_id, role and name. Decorators let a view
#                 run only when the access rule passes. No function returns or
#                 logs a password hash to a caller that renders pages.
# Errors: Failed authentication returns None (never an exception, never a
#         reason). create_account() raises ValueError for invalid input and
#         sqlite3.IntegrityError for a duplicate email. Decorators redirect to
#         the login page when nobody is signed in and abort with 403 when the
#         signed-in user lacks permission (400 if the route lacks the expected
#         URL parameter). An unsafe DB_SCHEMA identifier raises RuntimeError.

import hmac
import logging
import re
import secrets
from functools import wraps

from flask import abort, current_app, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..config import (MIN_PASSWORD_LENGTH, ROLE_STAFF, ROLE_STUDENT,
                      SESSION_CSRF_KEY, SESSION_NAME_KEY, SESSION_ROLE_KEY,
                      SESSION_USER_ID_KEY, VALID_ROLES)
from ..db import insert_record, transaction

log = logging.getLogger(__name__)

# Hash of a throwaway password. When an email is unknown we still run one full
# hash comparison against this value so response time does not reveal whether
# the account exists (timing side channel).
_DUMMY_HASH = generate_password_hash("never-a-real-password")

# Caps stop oversized values from reaching the hasher or the database.
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 1024

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# =============================================================================
# QUERY LAYER  (table/column names come from config.DB_SCHEMA)
# =============================================================================
def _ident(name):
    """Validate a table/column name from config and return it double-quoted.

    Identifiers cannot be bound as SQL parameters, so their shape is
    whitelisted instead. This keeps a bad DB_SCHEMA edit from becoming SQL
    injection.
    """
    if not isinstance(name, str) or not _IDENTIFIER.match(name):
        raise RuntimeError(f"Unsafe or invalid DB_SCHEMA identifier: {name!r}")
    return f'"{name}"'


def _database_path():
    """Return the shared database path chosen by create_app()."""
    return current_app.config["DATABASE"]


def _select_user(where_key, value, include_hash):
    """Fetch one user row as a dict, or None.

    `where_key` is 'email' or 'id' (a DB_SCHEMA key, never user input). The
    SELECT aliases each column to a FIXED name (id, name, email, role,
    password_hash), so the rest of this module never depends on real names.
    """
    schema = current_app.config["DB_SCHEMA"]
    cols = schema["columns"]
    select = [f"{_ident(cols['id'])} AS id", f"{_ident(cols['name'])} AS name",
              f"{_ident(cols['email'])} AS email", f"{_ident(cols['role'])} AS role"]
    if include_hash:
        select.append(f"{_ident(cols['password_hash'])} AS password_hash")
    where = f"{_ident(cols[where_key])} = ?"
    if where_key == "email":
        where += " COLLATE NOCASE"  # emails are case-insensitive
    sql = (f"SELECT {', '.join(select)} FROM {_ident(schema['table'])} "
           f"WHERE {where} LIMIT 1")
    with transaction(_database_path()) as connection:
        row = connection.execute(sql, (value,)).fetchone()  # value is bound
    return dict(row) if row else None


def find_user_by_id(user_id):
    """Return a user dict (no password hash) for `user_id`, or None."""
    return _select_user("id", user_id, include_hash=False)


# =============================================================================
# ACCOUNTS AND AUTHENTICATION  (Requirement 5)
# =============================================================================
def create_account(name, email, password, role):
    """Create a user with a hashed password and return the new user id.

    Staff accounts must be created only by trusted code (such as seed.py);
    never pass a role taken from a form or URL.
    """
    name = (name or "").strip()
    email = (email or "").strip()
    if not name:
        raise ValueError("Name is required.")
    if not _EMAIL_SHAPE.match(email) or len(email) > MAX_EMAIL_LENGTH:
        raise ValueError("A valid email address is required.")
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password is too long.")
    if role not in VALID_ROLES:
        raise ValueError(f"Role must be one of {VALID_ROLES}.")
    # insert_record() is the team's shared write helper; the enclosing
    # transaction commits on success and rolls back on any exception.
    with transaction(_database_path()) as connection:
        return insert_record(connection, "users", name=name, email=email,
                             password_hash=generate_password_hash(password),
                             role=role)


def authenticate(email, password):
    """Return the user dict (no hash) if the credentials are valid, else None.

    Unknown email, wrong password, malformed input and an unexpected stored
    role all return None, so callers can show one generic message.
    """
    email = (email or "").strip()
    if (not email or not password or len(email) > MAX_EMAIL_LENGTH
            or len(password) > MAX_PASSWORD_LENGTH):
        return None
    user = _select_user("email", email, include_hash=True)
    # Always run one hash comparison, even for unknown emails (see _DUMMY_HASH).
    stored_hash = user["password_hash"] if user else _DUMMY_HASH
    password_ok = check_password_hash(stored_hash, password)
    if user is None or not password_ok:
        return None
    if user["role"] not in VALID_ROLES:
        log.error("User id %s has invalid role %r", user["id"], user["role"])
        return None
    user.pop("password_hash", None)  # the hash never leaves this function
    return user


# =============================================================================
# SESSION HELPERS
# =============================================================================
def start_session(user):
    """Replace any existing session with one for `user` (prevents fixation)."""
    session.clear()
    session[SESSION_USER_ID_KEY] = user["id"]
    session[SESSION_ROLE_KEY] = user["role"]
    session[SESSION_NAME_KEY] = user["name"]
    session.permanent = True  # honour PERMANENT_SESSION_LIFETIME


def end_session():
    """Remove every key from the session (identity, role, name, CSRF token)."""
    session.clear()


def current_user():
    """Return {'id', 'role', 'name'} for the signed-in user, or None."""
    user_id = session.get(SESSION_USER_ID_KEY)
    role = session.get(SESSION_ROLE_KEY)
    if user_id is None or role not in VALID_ROLES:
        return None  # a half-set session counts as logged out
    return {"id": user_id, "role": role, "name": session.get(SESSION_NAME_KEY)}


def home_for_role(role):
    """Return the landing-page URL for a role (used after login)."""
    if role == ROLE_STAFF:
        return url_for("staff.staff_home")
    return url_for("student.student_home")


# =============================================================================
# CSRF HELPERS  (session-bound token, no extra dependency)
# =============================================================================
def csrf_token():
    """Return this session's CSRF token, creating it on first use."""
    if SESSION_CSRF_KEY not in session:
        session[SESSION_CSRF_KEY] = secrets.token_urlsafe(32)
    return session[SESSION_CSRF_KEY]


def csrf_is_valid():
    """True if the submitted form token matches the session token."""
    expected = session.get(SESSION_CSRF_KEY, "")
    submitted = request.form.get("csrf_token", "")
    # compare_digest avoids leaking match length through timing.
    return bool(expected) and hmac.compare_digest(expected, submitted)


# =============================================================================
# ACCESS DECORATORS  (Requirement 6: enforced on the server, not in the UI)
# Place them BELOW @bp.route(...). Teammates import these.
# =============================================================================
def login_required(view):
    """Allow the view only for signed-in users; others go to the login page."""

    @wraps(view)  # keep the view's name so Flask routing still works
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(required_role):
    """Allow the view only for users whose role equals `required_role`.

    Example: @role_required("staff") on the equipment registration route.
    """
    # Fail fast on typos such as role_required("admin") at import time.
    if required_role not in VALID_ROLES:
        raise ValueError(f"role_required: unknown role {required_role!r}")

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return redirect(url_for("auth.login"))  # not signed in
            if user["role"] != required_role:
                abort(403)  # signed in, but the wrong role
            return view(*args, **kwargs)

        return wrapped

    return decorator


def owner_or_staff_required(param_name="student_id"):
    """Allow staff, or the student whose id equals the URL parameter.

    The identity compared always comes from the signed session, never from a
    form field or query string. Both forms work:
        @owner_or_staff_required
        @owner_or_staff_required("student_id")
    """
    # Bare usage: Python passes the view itself as `param_name`.
    if callable(param_name):
        return owner_or_staff_required("student_id")(param_name)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return redirect(url_for("auth.login"))  # not signed in
            if user["role"] == ROLE_STAFF:
                return view(*args, **kwargs)  # staff may open any student
            requested = kwargs.get(param_name)
            if requested is None:
                abort(400)  # route lacks the expected URL parameter
            # Compare as strings so int/str types cannot cause a mismatch.
            if str(requested) != str(user["id"]):
                abort(403)  # a student asking for someone else's data
            return view(*args, **kwargs)

        return wrapped

    return decorator


# =============================================================================
# PRIVATE RECORDS  (ownership-filtered reads, as in Pranav's handoff example)
# =============================================================================
def get_student_records(student_id):
    """Return a student's reservations and loans, or None if not a student.

    Every query filters by `user_id = ?`, so the rows returned belong to that
    one student. The caller must already have passed
    @owner_or_staff_required. Only display fields are selected; no password
    hash is ever read here.
    """
    student = find_user_by_id(student_id)
    if student is None or student["role"] != ROLE_STUDENT:
        return None
    with transaction(_database_path()) as connection:
        reservations = connection.execute(
            "SELECT r.id, e.name AS equipment_name, e.asset_id, r.pickup_date, "
            "r.return_date, r.status FROM reservations r "
            "JOIN equipment e ON e.id = r.equipment_id "
            "WHERE r.user_id = ? ORDER BY r.pickup_date DESC, r.id DESC",
            (student["id"],)).fetchall()
        loans = connection.execute(
            "SELECT l.id, e.name AS equipment_name, e.asset_id, l.checkout_date, "
            "l.due_date, l.actual_return_date, l.status FROM loans l "
            "JOIN equipment e ON e.id = l.equipment_id "
            "WHERE l.user_id = ? ORDER BY l.checkout_date DESC, l.id DESC",
            (student["id"],)).fetchall()
    return {"student": {"id": student["id"], "name": student["name"],
                        "email": student["email"]},
            "reservations": [dict(r) for r in reservations],
            "loans": [dict(r) for r in loans]}
