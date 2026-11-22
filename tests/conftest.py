# Name: conftest.py
# Description: Shared pytest fixtures for the CampusGear test suite. Gives
#              every test its own temporary SQLite database (so no test touches
#              instance/campusgear.sqlite3), and provides an `app`, a `client`
#              and helper functions for logging in with CSRF tokens.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: Run with pytest from the repository root (pytest.ini adds the
#                src folder to the import path).
# Postconditions: Each test starts with a fresh database. The `seeded_app`
#                 fixture holds Student A (id 1), Student B (id 2) and a staff
#                 member (id 3), plus one equipment item, reservation and loan
#                 per student.
# Errors: Fixture setup failures surface as pytest errors for the affected test.

import pytest

from campusgear import create_app
from campusgear.business_logic.user_access import create_account
from campusgear.db import initialize, insert_record, transaction

# Credentials used only by the tests (separate from seed.py's local accounts).
STUDENT_A = ("Student A", "student.a@ku.edu", "StudentA-pass-123", "student")
STUDENT_B = ("Student B", "student.b@ku.edu", "StudentB-pass-123", "student")
STAFF = ("Staff Member", "staff@ku.edu", "Staff-pass-12345", "staff")


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Point every test (including navigation tests) at a throwaway database."""
    monkeypatch.setenv("CAMPUSGEAR_DB_PATH", str(tmp_path / "test.sqlite3"))


def make_app(**overrides):
    """Create the app in testing mode with optional config overrides."""
    config = {"TESTING": True, "ENABLE_TEST_ROUTES": True}
    config.update(overrides)
    return create_app(config)


@pytest.fixture()
def app():
    """Empty app (tables created, no users)."""
    return make_app()


@pytest.fixture()
def seeded_app(app):
    """App with two students, one staff member and sample private records."""
    with app.app_context():
        for name, email, password, role in (STUDENT_A, STUDENT_B, STAFF):
            create_account(name, email, password, role)
        with transaction(app.config["DATABASE"]) as connection:
            for user_id, asset, item in ((1, "KU-001", "Raspberry Pi Kit"),
                                         (2, "KU-002", "Camera Kit")):
                equipment = insert_record(
                    connection, "equipment", asset_id=asset, name=item,
                    category="Demo", description="Demo item", status="checked_out")
                insert_record(connection, "reservations", user_id=user_id,
                              equipment_id=equipment, pickup_date="2026-11-03",
                              return_date="2026-11-10", status="checked_out")
                insert_record(connection, "loans", user_id=user_id,
                              equipment_id=equipment, checkout_date="2026-11-03",
                              due_date="2026-11-10")
    return app


@pytest.fixture()
def client(seeded_app):
    """Test client for the seeded app."""
    return seeded_app.test_client()


def get_token(client):
    """Return the session's CSRF token, loading a page that creates it if needed.

    A signed-in user's pages contain the logout form (which creates the token);
    an anonymous user's /login page does.
    """
    def _read():
        with client.session_transaction() as sess:
            return sess.get("_csrf_token")

    token = _read()
    if not token:
        client.get("/")        # signed-in pages render the logout form
        token = _read()
    if not token:
        client.get("/login")   # anonymous: the login form creates the token
        token = _read()
    return token


def login(client, account):
    """POST valid or invalid credentials for an account tuple."""
    _name, email, password, _role = account
    return client.post("/login", data={
        "email": email, "password": password, "csrf_token": get_token(client)})


def logout(client):
    """POST /logout with the session's CSRF token."""
    return client.post("/logout", data={"csrf_token": get_token(client)})
