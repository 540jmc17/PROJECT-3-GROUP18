# Name: test_borrowing_history.py
# Description: Tests the student borrowing history page for Requirement 26
#              (View Borrowing History). Checks that a student sees each of
#              their loans with the equipment name, checkout date, and return
#              date; that active loans are not shown as returned; and that a
#              student can never see another student's history.
# Programmer: Karim Lakhani and Ahmed Gharib, with code-drafting assistance from Claude (Anthropic).
# Dates: November 22, 2026
# Revisions: None
# Preconditions: The seeded test database from conftest.py is available.
#                Student A (ID 1) has an active Raspberry Pi Kit loan and
#                Student B (ID 2) has an active Camera Kit loan.
# Postconditions: Passing tests confirm the history page lists the right
#                 records for the signed-in student only, shows return dates
#                 for returned loans, and rejects guests and staff.
# Errors: An assertion fails if the page shows the wrong student's records,
#         a wrong date, an active loan as returned, or an unexpected status code.

import re

from campusgear.db import insert_record, transaction
from conftest import STAFF, STUDENT_A, STUDENT_B, get_token, login, logout


HISTORY_URL = "/student/loans/history"


def add_returned_loan(database, user_id=1):
    """Give a student a finished loan (a Tripod borrowed and returned in October)."""
    with transaction(database) as connection:
        item_id = insert_record(connection, "equipment", asset_id="KU-003",
                                name="Tripod", category="Demo",
                                description="Test item", status="available")
        insert_record(connection, "loans", user_id=user_id, equipment_id=item_id,
                      checkout_date="2026-10-01", due_date="2026-10-08",
                      actual_return_date="2026-10-07", status="returned")


def test_history_shows_returned_and_active_loans(client, seeded_app):
    add_returned_loan(seeded_app.config["DATABASE"])
    login(client, STUDENT_A)

    # The student home page links to the history page.
    assert f'href="{HISTORY_URL}"' in client.get("/student").get_data(as_text=True)

    response = client.get(HISTORY_URL)
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # The returned Tripod shows its name, checkout date, and return date in one row.
    assert re.search(r"Tripod</td>\s*<td>KU-003</td>\s*"
                     r"<td><time datetime=\"2026-10-01\">2026-10-01</time></td>\s*"
                     r"<td><time datetime=\"2026-10-07\">2026-10-07</time></td>", html)

    # The active Raspberry Pi Kit is listed but marked as not returned.
    assert re.search(r"Raspberry Pi Kit</td>\s*<td>KU-001</td>\s*"
                     r"<td><time datetime=\"2026-11-03\">2026-11-03</time></td>\s*"
                     r"<td>Not yet returned", html)

    # Newest checkout first: the November loan appears before the October one.
    assert html.index("Raspberry Pi Kit") < html.index("Tripod")


def test_history_only_shows_own_records(client, seeded_app):
    add_returned_loan(seeded_app.config["DATABASE"], user_id=1)

    # Student B must not see Student A's items, even by adding a query value.
    login(client, STUDENT_B)
    html = client.get(f"{HISTORY_URL}?student_id=1").get_data(as_text=True)
    assert "Camera Kit" in html
    assert "Raspberry Pi Kit" not in html and "Tripod" not in html

    # Student A sees their own items and not Student B's.
    logout(client)
    login(client, STUDENT_A)
    html = client.get(HISTORY_URL).get_data(as_text=True)
    assert "Raspberry Pi Kit" in html and "Tripod" in html
    assert "Camera Kit" not in html


def test_history_updates_after_staff_return(client, seeded_app):
    # Staff record a return; the student's history then shows the return date.
    login(client, STAFF)
    client.post("/staff/returns", data=dict(loan_id=1, actual_return_date="2026-11-09",
                                            condition="good", csrf_token=get_token(client)))
    logout(client)
    login(client, STUDENT_A)
    html = client.get(HISTORY_URL).get_data(as_text=True)
    assert '<time datetime="2026-11-09">2026-11-09</time>' in html
    assert "<td>Not yet returned" not in html


def test_empty_history_message(client, seeded_app):
    with transaction(seeded_app.config["DATABASE"]) as connection:
        connection.execute("DELETE FROM loans WHERE user_id = 1")
    login(client, STUDENT_A)
    assert "You have not borrowed any equipment yet." in client.get(
        HISTORY_URL).get_data(as_text=True)


def test_history_is_student_only(client):
    # Guests are sent to login; staff are forbidden from the student page.
    assert client.get(HISTORY_URL).status_code == 302
    login(client, STAFF)
    assert client.get(HISTORY_URL).status_code == 403
