# Name: test_active_loans.py
# Description: Tests the student active-loans page for Requirement 16
#              (Display Due Dates). Checks that each checked-out item appears
#              beside its correct due date and that each student sees only
#              their own loans. Also checks the page after equipment is
#              returned and when a guest or staff member tries to open it.
# Programmer: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
# Dates: November 19, 2026
# Preconditions: The Flask test client and a seeded test database are available.
#                The test data gives Student A (user ID 1) the Raspberry Pi Kit
#                and Student B the Camera Kit. Login and logout helpers allow
#                the tests to switch between users.
# Postconditions: Passing tests confirm that the student home page links to
#                 active loans, the expected items and dates appear for each
#                 borrower tested, and returning Student A's last item shows
#                 the empty-list message. Guests receive a redirect (302),
#                 and signed-in staff receive a forbidden response (403).
# Errors: An assertion fails if the page shows the wrong item or date,
#         exposes another student's equipment, still lists a returned item,
#         or gives an unexpected response to a guest or staff member.

import re

from campusgear.db import insert_record, transaction
from conftest import STAFF, STUDENT_A, STUDENT_B, login, logout


# All three tests request this same page.
ACTIVE_LOANS_URL = "/student/loans/active"


def test_due_dates_match_equipment_and_exclude_other_students(client, seeded_app):
    # pytest supplies both arguments. The client makes requests to the Flask
    # app, and seeded_app gives us access to the database used by this test.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        # Student A already has the Raspberry Pi Kit. Add a Tripod with a
        # different due date so the test can detect a swap between the two dates.
        item_id = insert_record(connection, "equipment", asset_id="KU-003",
                                name="Tripod", category="Demo", description="Test item",
                                status="checked_out")

        # Use the new Tripod's database ID to link it to Student A's loan.
        insert_record(connection, "loans", user_id=1, equipment_id=item_id,
                      checkout_date="2026-11-03", due_date="2026-11-15")

    # Sign in as Student A and check that their home page links to active loans.
    # Each assert states something that must be true for the test to pass.
    login(client, STUDENT_A)
    assert f'href="{ACTIVE_LOANS_URL}"' in client.get("/student").get_data(as_text=True)

    # Put Student B's ID in the URL while Student A is still signed in.
    # The page should load (200) and still show Student A's equipment.
    response = client.get(f"{ACTIVE_LOANS_URL}?student_id=2")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Each pattern looks for three adjacent table cells containing the item
    # name, asset ID, and due date. The \s* allows spaces or line breaks
    # between cells, so indenting the HTML does not break the test.
    assert re.search(r"Raspberry Pi Kit</td>\s*<td>KU-001</td>\s*"
                     r'<td><time datetime="2026-11-10">2026-11-10</time>', html)
    assert re.search(r"Tripod</td>\s*<td>KU-003</td>\s*"
                     r'<td><time datetime="2026-11-15">2026-11-15</time>', html)

    # The Camera Kit belongs to Student B and should be absent from A's page.
    assert "Camera Kit" not in html

    # Switch the signed-in account. Now B should see the Camera Kit,
    # and neither of Student A's items should appear.
    logout(client)
    login(client, STUDENT_B)
    html = client.get(ACTIVE_LOANS_URL).get_data(as_text=True)
    assert "Camera Kit" in html
    assert "Raspberry Pi Kit" not in html
    assert "Tripod" not in html


def test_returned_equipment_disappears_from_active_loans(client, seeded_app):
    # First establish that the Raspberry Pi Kit is visible before the return.
    # The b prefix makes this a byte string because response.data contains bytes.
    login(client, STUDENT_A)
    assert b"Raspberry Pi Kit" in client.get(ACTIVE_LOANS_URL).data

    # Simulate a return directly in the test database.
    # The update marks all loans for user 1 (Student A) as returned.
    with transaction(seeded_app.config["DATABASE"]) as connection:
        connection.execute(
            "UPDATE loans SET status = 'returned', actual_return_date = ? WHERE user_id = ?",
            ("2026-11-08", 1),
        )

    # Request the page again after the update. It should load successfully,
    # hide the returned kit, and tell the student that nothing is checked out.
    response = client.get(ACTIVE_LOANS_URL)
    assert response.status_code == 200
    assert b"Raspberry Pi Kit" not in response.data
    assert b"You have no equipment checked out." in response.data


def test_active_loans_requires_student_login(client):
    # A guest who opens the page should receive a redirect (HTTP 302).
    assert client.get(ACTIVE_LOANS_URL).status_code == 302

    # Staff can sign in, but this page requires the student role.
    login(client, STAFF)
    assert client.get(ACTIVE_LOANS_URL).status_code == 403