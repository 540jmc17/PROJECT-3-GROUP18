"""
================================================================================
Name:          seed_data.py
Description:   Populates a fresh database with sample accounts and equipment so
               the application can be demonstrated immediately after cloning.
               Supplies the "sample records" that step 1 of the Requirement 1
               and Requirement 3 verification procedures call for, and the
               Student A / Student B pair that Requirement 6's procedure needs.

Programmer:    Pranav Reddy, Cameren Green
Created:       11/07/2026
Revisions:     11/07/2026 - Initial version for Sprint 1.

Preconditions: The database has been created by create_app (which calls
               init_db). Run this script from the project root.
Postconditions:Four user accounts and eight equipment items exist. Running the
               script twice does not duplicate anything: existing rows are
               detected and skipped.
Errors:        Prints a message and exits with status 1 if the database cannot
               be opened. Individual duplicate rows are skipped silently rather
               than aborting the whole seed.

External sources:
  - Claude (Anthropic) assisted with drafting this module and its comments.

DEMO ACCOUNTS CREATED BY THIS SCRIPT
  staff:   avery.staff@ku.edu    / StaffPass123
  student: student.a@ku.edu      / StudentPass123
  student: student.b@ku.edu      / StudentPass123
  student: karim.demo@ku.edu     / StudentPass123

  These are intentionally weak, publicly documented passwords for a local
  course demo. They must never be reused anywhere real.
================================================================================
"""

import sys

from app import create_app
from business_logic import equipment_mgmt, user_access
from data_access import database


# ==============================================================================
# SAMPLE DATA
# Two students are required, not one: Requirement 6's verification procedure
# signs in as Student A and then tries to read Student B's records.
# ==============================================================================

SAMPLE_USERS = [
    # (name,            email,                  password,         role)
    ("Avery Chen",      "avery.staff@ku.edu",   "StaffPass123",   "staff"),
    ("Student A",       "student.a@ku.edu",     "StudentPass123", "student"),
    ("Student B",       "student.b@ku.edu",     "StudentPass123", "student"),
    ("Karim Lakhani",   "karim.demo@ku.edu",    "StudentPass123", "student"),
]

SAMPLE_EQUIPMENT = [
    # (name,                    category,      description,                                      asset_id,     condition)
    ("Canon EOS R50",           "Camera",      "Mirrorless camera body with 18-45mm lens.",      "KU-CAM-001", "good"),
    ("Canon EOS R50",           "Camera",      "Second body, identical model, separate asset.",  "KU-CAM-002", "good"),
    ("Rode NT-USB Microphone",  "Audio",       "USB condenser microphone with pop filter.",      "KU-AUD-011", "good"),
    ("Zoom H5 Recorder",        "Audio",       "Portable four-track field recorder.",            "KU-AUD-012", "fair"),
    ("Raspberry Pi 5 Kit",      "Electronics", "Pi 5, 8GB, with case, PSU, and microSD card.",   "KU-ELC-031", "good"),
    ("Soldering Station Kit",   "Electronics", "Temperature-controlled iron, stand, and solder.", "KU-ELC-032", "good"),
    ("TI-Nspire CX II",         "Calculator",  "Graphing calculator with charging cable.",       "KU-CAL-051", "good"),
    ("Dell Latitude 5450",      "Laptop",      "14-inch laptop, Windows 11, charger included.",  "KU-LAP-071", "good"),
]


# ==============================================================================
# SEEDING
# ==============================================================================

def seed_users():
    """
    Create the sample accounts, skipping any that already exist.

    Inputs:  None.
    Outputs: int - how many accounts were created on this run.

    Preconditions:  Application context active.
    Postconditions: Every account in SAMPLE_USERS exists. Passwords are stored
                    only as hashes, exactly as a real signup would store them.
    Errors:         None propagate. A duplicate email is caught and skipped.
    """
    created = 0

    for name, email, password, role in SAMPLE_USERS:
        try:
            user_access.create_user(name, email, password, role)
            created += 1
            print(f"  created {role:<8} {email}")
        except ValueError:
            # Raised when the email is already registered, which is the normal
            # case on a second run. Not an error worth stopping for.
            print(f"  skipped {role:<8} {email} (already exists)")

    return created


def seed_equipment():
    """
    Create the sample equipment, skipping any asset ID already registered.

    Inputs:  None.
    Outputs: int - how many items were created on this run.

    Preconditions:  Application context active.
    Postconditions: Every item in SAMPLE_EQUIPMENT exists with status
                    'available', so the catalog is populated for the demo.
    Errors:         None propagate. A duplicate asset ID is caught and skipped,
                    which doubles as a live check that Requirement 2's
                    duplicate rejection works.
    """
    created = 0

    for name, category, description, asset_id, condition in SAMPLE_EQUIPMENT:
        try:
            equipment_mgmt.register_equipment(
                name=name,
                category=category,
                description=description,
                asset_id=asset_id,
                condition=condition,
            )
            created += 1
            print(f"  created {asset_id}  {name}")
        except equipment_mgmt.ValidationError:
            print(f"  skipped {asset_id}  {name} (already registered)")

    return created


def main():
    """
    Seed the database and report what was added.

    Inputs:  None (command-line script).
    Outputs: Exit status 0 on success, 1 on failure.

    Preconditions:  Run from the project root so `import app` resolves.
    Postconditions: The database holds the sample users and equipment.
    Errors:         Any unexpected exception is reported and turned into a
                    non-zero exit status rather than a bare traceback.
    """
    app = create_app()

    with app.app_context():
        print("Seeding CampusGear database...")
        print(f"Database: {app.config['DATABASE']}\n")

        print("Users:")
        users_created = seed_users()

        print("\nEquipment:")
        equipment_created = seed_equipment()

        # Read the totals back out so the summary reflects what is actually in
        # the database, not just what this run inserted.
        total_users = database.query_one("SELECT COUNT(*) AS n FROM users")["n"]
        total_equipment = database.query_one("SELECT COUNT(*) AS n FROM equipment")["n"]

        print(
            f"\nDone. Added {users_created} user(s) and {equipment_created} item(s)."
        )
        print(f"Database now holds {total_users} user(s) and {total_equipment} item(s).")
        print("\nSign in as staff with:   avery.staff@ku.edu / StaffPass123")
        print("Sign in as student with: student.a@ku.edu   / StudentPass123")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - top-level script guard
        print(f"Seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)
