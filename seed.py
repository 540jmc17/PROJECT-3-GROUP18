# Name: seed.py
# Description: Standalone development utility that creates the three local
#              test accounts (Student A, Student B and a Staff Member) through
#              the login team's create_account() function, so their passwords
#              are stored as werkzeug hashes. It first runs db.initialize()
#              (safe to repeat). It is NON-destructive by default: accounts
#              that already exist are skipped. --reset deletes the whole
#              database file (all teams' data) after confirmation, and
#              --sample-data adds one equipment item, reservation and loan per
#              student so the private-records page has something to show.
#              For local testing only; never run against real data.
# Programmer: Zema Samuel
# Dates: November 7, 2026
# Revisions: None
# Preconditions: Run from the repository root with the project's dependencies
#                installed. The database path is CAMPUSGEAR_DB_PATH, or the
#                default instance/campusgear.sqlite3.
# Postconditions: The users table contains the three seed accounts. With
#                 --sample-data, sample equipment, reservations and loans for
#                 the two students also exist (skipped if their asset IDs are
#                 already present).
# Errors: Declining the --reset prompt exits with status 1 and changes
#         nothing. sqlite3 errors (for example an unwritable path) propagate.
#         Duplicate accounts are reported and skipped, not treated as errors.

import argparse
import os
import secrets
import sqlite3
import sys
from pathlib import Path

# This script never serves requests, so a throwaway key avoids the startup warning.
os.environ.setdefault("CAMPUSGEAR_SECRET_KEY", secrets.token_hex(32))

# Make the src folder importable, exactly as app.py does.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from campusgear import create_app                                  # noqa: E402
from campusgear.business_logic.user_access import create_account  # noqa: E402
from campusgear.db import DEFAULT_PATH, insert_record, transaction  # noqa: E402

# Demo credentials for LOCAL TESTING ONLY: (name, email, password, role).
SEED_ACCOUNTS = [
    ("Student A", "student.a@ku.edu", "StudentA-pass-123", "student"),
    ("Student B", "student.b@ku.edu", "StudentB-pass-123", "student"),
    ("Staff Member", "staff@ku.edu", "Staff-pass-12345", "staff"),
]


def _confirm_reset(db_path):
    """Return True only if the operator types 'yes' to deleting the file."""
    reply = input(f"This DELETES the whole database {db_path}. Type 'yes' to continue: ")
    return reply.strip().lower() == "yes"


def seed_accounts():
    """Create each seed account; return the list of emails that were new."""
    created = []
    for name, email, password, role in SEED_ACCOUNTS:
        try:
            create_account(name, email, password, role)
            created.append(email)
        except sqlite3.IntegrityError:
            print(f"  skipped (already exists): {email}")
    return created


def seed_sample_data(app):
    """Add one equipment item, reservation and loan for each student."""
    db = app.config["DATABASE"]
    with transaction(db) as connection:
        ids = {row["email"]: row["id"] for row in connection.execute(
            "SELECT id, email FROM users WHERE role = 'student'")}
        samples = [("student.a@ku.edu", "KU-001", "Raspberry Pi Kit", "Lab gear"),
                   ("student.b@ku.edu", "KU-002", "Camera Kit", "Photography")]
        for email, asset, name, category in samples:
            exists = connection.execute(
                "SELECT 1 FROM equipment WHERE asset_id = ?", (asset,)).fetchone()
            if exists or email not in ids:
                continue
            item = insert_record(connection, "equipment", asset_id=asset, name=name,
                                 category=category, description=f"{name} for demo use.",
                                 status="checked_out")
            reservation = insert_record(connection, "reservations", user_id=ids[email],
                                        equipment_id=item, pickup_date="2026-11-03",
                                        return_date="2026-11-10", status="checked_out")
            insert_record(connection, "loans", user_id=ids[email], equipment_id=item,
                          reservation_id=reservation, checkout_date="2026-11-03",
                          due_date="2026-11-10")


def main(argv):
    """Parse options, optionally reset, then seed."""
    parser = argparse.ArgumentParser(description="Create local test accounts.")
    parser.add_argument("--reset", action="store_true",
                        help="delete the entire database file first (asks to confirm)")
    parser.add_argument("--yes", action="store_true",
                        help="skip the --reset confirmation prompt")
    parser.add_argument("--sample-data", action="store_true",
                        help="also add sample equipment, reservations and loans")
    args = parser.parse_args(argv)

    db_path = Path(os.environ.get("CAMPUSGEAR_DB_PATH") or DEFAULT_PATH)
    if args.reset and db_path.exists():
        if not args.yes and not _confirm_reset(db_path):
            print("Aborted; nothing changed.")
            return 1
        db_path.unlink()  # removed; create_app() below recreates the tables

    app = create_app()  # runs db.initialize() on the chosen path
    with app.app_context():
        created = seed_accounts()
        if args.sample_data:
            seed_sample_data(app)
    print(f"Database: {app.config['DATABASE']}")
    print(f"Accounts created: {len(created)} (existing ones were left unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
