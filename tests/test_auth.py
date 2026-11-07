# Module Name: test_auth.py
# Description: Checks login, privacy, and the menu options visible after login.
# Inputs: Test accounts in an isolated SQLite database.
# Outputs: pytest results for authentication, access, and role-specific menus.
# Implementation author: Zema Samuel (original login and privacy tests).
# External Sources / Attribution: OpenAI Codex generated the Req 7 menu assertions.
# Creation Date: November 7, 2026.

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

from campusgear import create_app
from campusgear.business_logic.user_access import create_account
from campusgear.db import transaction
from conftest import STAFF, STUDENT_A, STUDENT_B, get_token, login, logout, make_app

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERIC = "Invalid credentials"


def _alert_text(response):
    """Return the text of the error alert on a login response."""
    match = re.search(r'class="alert alert-error"[^>]*>([^<]*)<', response.get_data(as_text=True))
    return match.group(1).strip() if match else None


# =============================================================================
# REQUIREMENT 5: LOGIN / LOGOUT
# =============================================================================
def test_student_login_reaches_student_interface(client):
    response = login(client, STUDENT_A)
    assert response.status_code == 302 and response.location.endswith("/student")
    page = client.get("/student").data
    assert b"Student Interface" in page
    assert b"Browse equipment to borrow" in page
    assert b"My reservations &amp; loans" in page
    assert b"Add equipment" not in page


def test_staff_login_reaches_staff_interface(client):
    response = login(client, STAFF)
    assert response.status_code == 302 and response.location.endswith("/staff")
    page = client.get("/staff").data
    assert b"Staff Interface" in page
    assert b"View inventory" in page
    assert b"Add equipment" in page
    assert b"My reservations &amp; loans" not in page


def test_session_holds_user_id_and_role(client):
    login(client, STUDENT_A)
    with client.session_transaction() as sess:
        assert sess["user_id"] == 1 and sess["role"] == "student"


def test_wrong_password_gives_single_generic_message(client):
    response = client.post("/login", data={
        "email": STUDENT_A[1], "password": "wrong-password", "csrf_token": get_token(client)})
    assert response.status_code == 401 and _alert_text(response) == GENERIC


def test_unknown_email_gives_identical_message(client):
    wrong_pw = client.post("/login", data={
        "email": STUDENT_A[1], "password": "nope", "csrf_token": get_token(client)})
    unknown = client.post("/login", data={
        "email": "nobody@ku.edu", "password": "nope", "csrf_token": get_token(client)})
    assert unknown.status_code == wrong_pw.status_code == 401
    assert _alert_text(unknown) == _alert_text(wrong_pw) == GENERIC


@pytest.mark.parametrize("email,password", [("", ""), ("student.a@ku.edu", ""), ("", "x"),
                                            ("a" * 400 + "@ku.edu", "x"), ("student.a@ku.edu", "x" * 5000)])
def test_blank_or_oversized_input_is_rejected_generically(client, email, password):
    response = client.post("/login", data={
        "email": email, "password": password, "csrf_token": get_token(client)})
    assert response.status_code == 401 and _alert_text(response) == GENERIC


def test_email_is_case_and_whitespace_insensitive(client):
    response = client.post("/login", data={
        "email": "  STUDENT.A@KU.EDU ", "password": STUDENT_A[2], "csrf_token": get_token(client)})
    assert response.status_code == 302


def test_failed_login_does_not_sign_anyone_in(client):
    client.post("/login", data={"email": STUDENT_A[1], "password": "bad",
                                "csrf_token": get_token(client)})
    with client.session_transaction() as sess:
        assert "user_id" not in sess and "role" not in sess
    assert client.get("/student").status_code == 302


def test_login_requires_valid_csrf_token(client):
    no_token = client.post("/login", data={"email": STUDENT_A[1], "password": STUDENT_A[2]})
    bad_token = client.post("/login", data={"email": STUDENT_A[1], "password": STUDENT_A[2],
                                            "csrf_token": "forged"})
    assert no_token.status_code == bad_token.status_code == 400


def test_login_page_has_form_and_hidden_csrf_field(client):
    html = client.get("/login").get_data(as_text=True)
    assert "<form" in html and 'type="hidden" name="csrf_token"' in html


def test_logout_flushes_entire_session(client):
    login(client, STUDENT_A)
    response = logout(client)
    assert response.status_code == 302 and response.location.endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess and "role" not in sess and "name" not in sess


def test_logged_out_user_cannot_reach_protected_pages(client):
    login(client, STUDENT_A)
    logout(client)
    for path in ("/student", "/staff", "/students/1/records", "/test/needs-login"):
        response = client.get(path)
        assert response.status_code == 302 and "/login" in response.location, path


def test_logout_message_is_shown_once(client):
    login(client, STUDENT_A)
    logout(client)
    assert b"You have been logged out." in client.get("/login").data
    assert b"You have been logged out." not in client.get("/login").data


def test_logout_rejects_get_and_missing_csrf(client):
    login(client, STUDENT_A)
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 400
    assert client.get("/student").status_code == 200  # still signed in


@pytest.mark.parametrize("path", ["/student", "/staff", "/students/1/records"])
def test_unauthenticated_requests_redirect_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302 and "/login" in response.location


def test_signed_in_user_visiting_login_is_redirected_home(client):
    login(client, STAFF)
    response = client.get("/login")
    assert response.status_code == 302 and response.location.endswith("/staff")


def test_session_is_replaced_at_login(client):
    """A token issued before login must not survive it (session fixation)."""
    before = get_token(client)
    login(client, STUDENT_A)
    assert get_token(client) != before


def test_role_cannot_be_chosen_by_the_client(client):
    client.post("/login", data={"email": STUDENT_A[1], "password": STUDENT_A[2],
                                "role": "staff", "csrf_token": get_token(client)})
    with client.session_transaction() as sess:
        assert sess["role"] == "student"
    assert client.get("/staff").status_code == 403


def test_menu_shows_sign_in_when_out_and_logout_when_in(client):
    assert b">Sign in</a>" in client.get("/").data
    login(client, STUDENT_A)
    html = client.get("/").get_data(as_text=True)
    assert 'action="/logout"' in html and ">Sign in</a>" not in html


# ---- Accounts and password hashing -----------------------------------------
def test_passwords_are_stored_as_hashes_not_plaintext(seeded_app):
    with transaction(seeded_app.config["DATABASE"]) as connection:
        rows = connection.execute("SELECT email, password_hash FROM users").fetchall()
    assert len(rows) == 3
    passwords = {STUDENT_A[1]: STUDENT_A[2], STUDENT_B[1]: STUDENT_B[2], STAFF[1]: STAFF[2]}
    for row in rows:
        assert row["password_hash"].startswith(("scrypt:", "pbkdf2:"))
        assert row["password_hash"] != passwords[row["email"]]
        assert check_password_hash(row["password_hash"], passwords[row["email"]])


def test_same_password_gets_different_salted_hashes(app):
    with app.app_context():
        create_account("One", "one@ku.edu", "SamePassword-1", "student")
        create_account("Two", "two@ku.edu", "SamePassword-1", "student")
        with transaction(app.config["DATABASE"]) as connection:
            hashes = [r[0] for r in connection.execute("SELECT password_hash FROM users")]
    assert hashes[0] != hashes[1]


def test_password_hash_never_appears_in_pages(client):
    login(client, STAFF)
    for path in ("/staff", "/students/1/records", "/students/2/records", "/"):
        assert b"scrypt:" not in client.get(path).data and b"pbkdf2:" not in client.get(path).data


@pytest.mark.parametrize("args", [
    ("", "ok@ku.edu", "Password-123", "student"),
    ("N", "not-an-email", "Password-123", "student"),
    ("N", "ok@ku.edu", "short", "student"),
    ("N", "ok@ku.edu", "Password-123", "admin"),
])
def test_create_account_rejects_invalid_input(app, args):
    with app.app_context(), pytest.raises(ValueError):
        create_account(*args)


def test_create_account_rejects_duplicate_email_case_insensitively(seeded_app):
    with seeded_app.app_context(), pytest.raises(sqlite3.IntegrityError):
        create_account("Copy", STUDENT_A[1].upper(), "Password-123", "student")


# =============================================================================
# REQUIREMENT 6: STUDENT PRIVACY AND ACCESS CONTROL
# =============================================================================
def test_student_can_read_own_records(client):
    login(client, STUDENT_A)
    response = client.get("/students/1/records")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Raspberry Pi Kit" in html and "KU-001" in html
    assert "Camera Kit" not in html and STUDENT_B[1] not in html


def test_horizontal_escalation_student_a_cannot_read_student_b(client):
    login(client, STUDENT_A)
    response = client.get("/students/2/records")
    assert response.status_code == 403
    assert b"Camera Kit" not in response.data and b"KU-002" not in response.data
    assert client.get("/test/student/2/records").status_code == 403


def test_student_gets_403_not_404_for_nonexistent_ids(client):
    """Same answer for real and fake ids, so ids cannot be enumerated."""
    login(client, STUDENT_A)
    assert client.get("/students/999/records").status_code == 403
    assert client.get("/students/2/records").status_code == 403


def test_vertical_escalation_student_cannot_use_staff_functions(client):
    login(client, STUDENT_A)
    assert client.get("/test/staff-only").status_code == 403
    assert client.get("/staff").status_code == 403


def test_staff_can_use_staff_functions_and_read_any_student(client):
    login(client, STAFF)
    assert client.get("/test/staff-only").status_code == 200
    assert client.get("/staff").status_code == 200
    assert b"Raspberry Pi Kit" in client.get("/students/1/records").data
    assert b"Camera Kit" in client.get("/students/2/records").data


def test_staff_asking_for_missing_or_non_student_record_gets_404(client):
    login(client, STAFF)
    assert client.get("/students/999/records").status_code == 404
    assert client.get("/students/3/records").status_code == 404  # id 3 is staff


def test_staff_cannot_open_student_interface(client):
    login(client, STAFF)
    assert client.get("/student").status_code == 403


def test_forbidden_page_is_clean(client):
    login(client, STUDENT_A)
    response = client.get("/students/2/records")
    assert b"403 Forbidden" in response.data
    assert b"Traceback" not in response.data and b"student.b@ku.edu" not in response.data


def test_owner_or_staff_decorator_works_without_parentheses(seeded_app):
    from campusgear.business_logic.user_access import owner_or_staff_required

    @seeded_app.route("/bare/<int:student_id>")
    @owner_or_staff_required
    def bare(student_id):
        return "ok"

    client = seeded_app.test_client()
    login(client, STUDENT_A)
    assert client.get("/bare/1").status_code == 200
    assert client.get("/bare/2").status_code == 403


def test_role_required_rejects_unknown_role():
    from campusgear.business_logic.user_access import role_required
    with pytest.raises(ValueError):
        role_required("admin")


def test_test_routes_do_not_exist_unless_enabled():
    client = make_app(ENABLE_TEST_ROUTES=False).test_client()
    assert client.get("/test/staff-only").status_code == 404


# Endpoints that are intentionally public. If a teammate adds a new public
# page, add its endpoint here on purpose; otherwise this test fails to warn
# that a route may be missing @login_required / @role_required.
PUBLIC_ENDPOINTS = {"static", "site.home", "site.catalog", "site.about",
                    "auth.login", "auth.logout"}


def test_every_non_public_route_blocks_anonymous_users(seeded_app):
    anonymous = seeded_app.test_client()
    for rule in seeded_app.url_map.iter_rules():
        if rule.endpoint in PUBLIC_ENDPOINTS or "GET" not in rule.methods:
            continue
        url = re.sub(r"<(?:int:)?\w+>", "1", rule.rule)
        status = anonymous.get(url).status_code
        assert status in (302, 401, 403), f"{rule.endpoint} ({url}) is open: HTTP {status}"


# =============================================================================
# SESSION HARDENING, HEADERS AND CONFIGURATION
# =============================================================================
def test_session_cookie_is_httponly_and_samesite_lax(client):
    cookie = login(client, STUDENT_A).headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Secure" not in cookie  # off by default so http://127.0.0.1 works


def test_session_cookie_secure_flag_follows_environment(monkeypatch):
    monkeypatch.setenv("CAMPUSGEAR_COOKIE_SECURE", "1")
    app = make_app()
    assert app.config["SESSION_COOKIE_SECURE"] is True
    app.config["SERVER_NAME"] = None
    client = app.test_client()
    with app.app_context():
        create_account(*STUDENT_A)
    cookie = client.post("/login", data={
        "email": STUDENT_A[1], "password": STUDENT_A[2], "csrf_token": get_token(client)},
        base_url="https://localhost").headers.get("Set-Cookie", "")
    assert "Secure" in cookie


def test_secret_key_comes_from_environment(monkeypatch):
    key = "k" * 40
    monkeypatch.setenv("CAMPUSGEAR_SECRET_KEY", key)
    assert create_app({"TESTING": False}).config["SECRET_KEY"] == key


def test_short_environment_secret_key_is_refused(monkeypatch):
    monkeypatch.setenv("CAMPUSGEAR_SECRET_KEY", "too-short")
    with pytest.raises(RuntimeError):
        create_app({"TESTING": False})


def test_missing_secret_key_falls_back_to_random_key(monkeypatch):
    monkeypatch.delenv("CAMPUSGEAR_SECRET_KEY", raising=False)
    first = create_app({"TESTING": False}).config["SECRET_KEY"]
    second = create_app({"TESTING": False}).config["SECRET_KEY"]
    assert first and second and first != second


def test_security_headers_present(client):
    headers = client.get("/login").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["Cache-Control"] == "no-store"
    assert client.get("/static/css/styles.css").headers.get("Cache-Control") != "no-store"


def test_db_schema_is_the_single_place_for_user_table_names(app):
    """Rename the table and every column; one DB_SCHEMA edit keeps login working."""
    schema = {"table": "accounts", "columns": {
        "id": "acct_id", "name": "full_name", "email": "mail",
        "password_hash": "pw_hash", "role": "user_role"}}
    with app.app_context():
        from werkzeug.security import generate_password_hash
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.execute("CREATE TABLE accounts (acct_id INTEGER PRIMARY KEY, "
                           "full_name TEXT, mail TEXT COLLATE NOCASE, pw_hash TEXT, user_role TEXT)")
        connection.execute("INSERT INTO accounts (full_name, mail, pw_hash, user_role) VALUES (?,?,?,?)",
                           ("Renamed Staff", "renamed@ku.edu", generate_password_hash("Renamed-pass-1"), "staff"))
        connection.commit()
        connection.close()
    app.config["DB_SCHEMA"] = schema  # <- the one-line change
    client = app.test_client()
    response = client.post("/login", data={
        "email": "renamed@ku.edu", "password": "Renamed-pass-1", "csrf_token": get_token(client)})
    assert response.status_code == 302 and response.location.endswith("/staff")


def test_unsafe_schema_identifier_is_refused(app):
    app.config["DB_SCHEMA"] = {"table": "users; DROP TABLE users", "columns": {
        "id": "id", "name": "name", "email": "email", "password_hash": "password_hash", "role": "role"}}
    client = app.test_client()
    with pytest.raises(RuntimeError):
        client.post("/login", data={"email": "a@ku.edu", "password": "x",
                                    "csrf_token": get_token(client)})


# =============================================================================
# seed.py (local test accounts)
# =============================================================================
def _run_seed(*args):
    return subprocess.run([sys.executable, str(REPO_ROOT / "seed.py"), *args], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=120)


def test_seed_script_creates_working_accounts_and_is_repeatable():
    first = _run_seed("--sample-data")
    again = _run_seed("--sample-data")
    assert first.returncode == 0 and "Accounts created: 3" in first.stdout
    assert again.returncode == 0 and "Accounts created: 0" in again.stdout
    client = make_app().test_client()
    assert login(client, ("Student A", "student.a@ku.edu", "StudentA-pass-123", "student")).status_code == 302
    assert b"KU-001" in client.get("/students/1/records").data
    assert client.get("/students/2/records").status_code == 403


def test_seed_reset_requires_confirmation():
    _run_seed()
    declined = subprocess.run([sys.executable, str(REPO_ROOT / "seed.py"), "--reset"], cwd=REPO_ROOT,
                              input="no\n", capture_output=True, text=True, timeout=120)
    assert declined.returncode == 1 and "Aborted" in declined.stdout
    assert _run_seed("--reset", "--yes").returncode == 0
