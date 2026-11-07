"""Req 7: verify the options shown after student and staff login."""
from conftest import STAFF, STUDENT_A, login, logout


def test_role_options_after_login(client):
    student = client.get(login(client, STUDENT_A).location)
    assert b"Browse equipment to borrow" in student.data
    assert b"My reservations &amp; loans" in student.data
    assert b"Add equipment" not in student.data

    logout(client)
    staff = client.get(login(client, STAFF).location)
    assert b"View inventory" in staff.data
    assert b"Add equipment" in staff.data
    assert b"My reservations &amp; loans" not in staff.data
