# Name: test_equipment.py
# Description: Tests for Requirement 2 (Equipment Registration) and
#              Requirement 3 (Equipment Catalog).
# Programmer: Ahmed (Mado) Gharib, with substantial code-drafting assistance from Claude (Anthropic).
# Dates: November 8, 2026
# Revisions: None
# Reviewed by: Ahmed Gharib
# External Sources / Attribution: Created with assistance from Claude (Anthropic). Uses pytest and the shared fixtures in conftest.py.
# Code Origin: Newly written for EECS 581 Project 3, Requirements 2 and 3.

from conftest import STAFF, STUDENT_A, get_token, login

FORM = {"name": "Canon Camera", "category": "Camera",
        "description": "DSLR with 18-55mm lens", "asset_id": "KU-CAM-100"}


def post_form(client, **overrides):
    data = dict(FORM, csrf_token=get_token(client))
    data.update(overrides)
    return client.post("/staff/equipment/new", data=data)


def test_staff_can_register_and_item_appears_in_catalog(client):
    login(client, STAFF)
    response = post_form(client)
    assert response.status_code == 302
    page = client.get("/catalog").get_data(as_text=True)
    assert "Canon Camera" in page and "KU-CAM-100" in page


def test_duplicate_asset_id_is_rejected(client):
    login(client, STAFF)
    post_form(client)
    response = post_form(client, name="Second Camera")
    assert response.status_code == 400
    assert "already registered" in response.get_data(as_text=True)
    assert "Second Camera" not in client.get("/catalog").get_data(as_text=True)


def test_missing_fields_are_rejected(client):
    login(client, STAFF)
    response = post_form(client, name="   ")
    assert response.status_code == 400
    assert "Please fill in" in response.get_data(as_text=True)


def test_student_cannot_open_or_submit_form(client):
    login(client, STUDENT_A)
    assert client.get("/staff/equipment/new").status_code == 403
    assert post_form(client).status_code == 403


def test_logged_out_user_is_sent_to_login(client):
    assert client.get("/staff/equipment/new").status_code == 302


def test_catalog_marks_unavailable_items(client):
    # Seeded items are checked out, so they must not show as available.
    login(client, STAFF)
    post_form(client)
    page = client.get("/catalog").get_data(as_text=True)
    assert "1 of 3 items available" in page
    assert "Unavailable (checked out)" in page
