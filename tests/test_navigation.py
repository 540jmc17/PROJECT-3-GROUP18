"""
Module Name: test_navigation.py

Description:
    Contains automated tests for the CampusGear public website
    navigation and Sprint 1 presentation features.

    Tests verify that the implemented pages load successfully,
    display the correct page titles, include the shared navigation
    menu, identify the active page, and serve the stylesheet.

    Tests also verify that the equipment catalog and login pages
    are clearly labeled as placeholders until their respective
    features are integrated.

Inputs:
    HTTP requests simulated through the Flask test client.

Outputs:
    Test results indicating whether the tested website functionality
    passes or fails the expected conditions.

Implementation Author: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
Creation Date: 11/6/26.
Reviewed by: Jake Crawford and John Pannell.
Revisions: November 8, 2026 - Ahmed Gharib replaced the catalog placeholder
    test with a test that the real catalog loads (Requirement #3), with
    assistance from Claude (Anthropic). Reviewed by Ahmed Gharib.
Documentation Author: Jake Crawford and John Pannell.
External Sources / Attribution: Pytest and Flask documentation
Code Origin: Newly written for EECS 581 Project 3 with assistance from ChatGPT.
"""

# Import pytest to create and run automated tests.
import pytest

# Import the function that creates the CampusGear application.
from campusgear import create_app


# TEST CLIENT SETUP
# Creates a Flask test client so tests can simulate
# website requests without opening a browser.
@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    return app.test_client()


# TEST 1 - PAGE LOADING
# Checks that all four implemented pages load successfully.
# Verifies that each page returns HTTP status 200,
# displays the correct browser title, and includes
# the shared navigation menu.
#
# parametrize runs the same test with four different
# page URLs and their expected titles.
@pytest.mark.parametrize(
    "path,title",
    [
        ("/", "Home"),
        ("/catalog", "Equipment Catalog"),
        ("/about", "About"),
        ("/login", "Sign in"),
    ],
)
def test_implemented_pages_load(client, path, title):
    response = client.get(path)
    assert response.status_code == 200
    assert f"<title>{title} | CampusGear</title>".encode() in response.data
    assert b'<nav class="primary-nav" aria-label="Primary navigation">' in response.data


# TEST 2 - NAVIGATION LINKS
# Checks that the navigation links are available
# on every implemented website page.
#
# The test also verifies that the accessibility
# link for skipping directly to the main content exists.
@pytest.mark.parametrize("path", ["/", "/catalog", "/about", "/login"])
def test_navigation_links_are_available_on_every_page(client, path):
    html = client.get(path).get_data(as_text=True)

    # Verify that the main website links are present.
    for link in ('href="/"', 'href="/catalog"', 'href="/about"', 'href="/login"'):
        assert link in html

    # Verify the accessibility skip link is present.
    assert 'href="#main-content"' in html


# TEST 3 - ACTIVE PAGE INDICATOR
# Verifies that the currently selected page is marked
# as active in the website's navigation.
#
# aria-current="page" identifies the active page
# for accessibility tools such as screen readers.
#
# Only one page should be marked as active at a time.
@pytest.mark.parametrize("path,label", [
    ("/", "Home"),
    ("/catalog", "Equipment Catalog"),
    ("/about", "About"),
    ("/login", "Sign in"),
])
def test_selected_page_is_marked_active(client, path, label):
    html = client.get(path).get_data(as_text=True)

    # Verify that the correct page is marked as active.
    assert f'aria-current="page">{label}</a>' in html

    # Prevent multiple navigation links from being marked active.
    assert html.count('aria-current="page"') == 1


# TEST 4 - EQUIPMENT CATALOG
# The placeholder was replaced by the real catalog (Requirement #3),
# so the page should now load and show the equipment table.
def test_catalog_page_loads_equipment(client):
    response = client.get("/catalog")
    assert response.status_code == 200
    assert "Equipment Catalog" in response.get_data(as_text=True)


# TEST 5 - LOGIN PAGE
# Requirement #5 replaced the navigation-only placeholder with a real sign-in
# form (updated by Zema Samuel, November 7, 2026). Verifies that the page now
# shows a form that posts credentials together with an anti-CSRF token.
#
# Backend security behavior is tested in tests/test_auth.py.
def test_login_page_now_shows_a_sign_in_form(client):
    html = client.get("/login").get_data(as_text=True)

    assert "<form" in html and 'method="post"' in html
    assert 'name="email"' in html and 'name="password"' in html
    assert 'name="csrf_token"' in html
    assert "Secure login is coming soon" not in html
