"""
================================================================================
Name:          config.py
Description:   Configuration values for the CampusGear Flask application:
               the database file location, the session signing key, and the
               cookie hardening flags that support Requirement 6.

Programmer:    Jake Crawford, John
Created:       11/07/2026
Revisions:     11/07/2026 - Initial version for Sprint 1.

Preconditions: None. This module defines constants only.
Postconditions:None.
Errors:        None.

External sources:
  - Claude (Anthropic) assisted with drafting this module and its comments.
  - Session cookie flags documented at
    https://flask.palletsprojects.com/en/stable/config/

SECURITY NOTE FOR THE TEAM
  SECRET_KEY below is a fixed development value so that every team member and
  the GTA get the same behaviour when they clone and run the repository. A real
  deployment must read it from an environment variable instead, because anyone
  who knows the key can forge a session cookie and sign in as any user. The
  code already supports this: set the CAMPUSGEAR_SECRET_KEY environment
  variable and it takes priority over the default.
================================================================================
"""

import os
from pathlib import Path

# Project root, resolved from this file so the paths below are correct no
# matter which directory the application is launched from.
BASE_DIR = Path(__file__).parent


class Config:
    """
    Default configuration, loaded by create_app via app.config.from_object.

    Inputs:  None.
    Outputs: Class attributes read by Flask.
    Preconditions:  None.
    Postconditions: None.
    Errors:         None.
    """

    # --- Database ------------------------------------------------------------
    # Kept in an instance/ folder so the .db file is easy to gitignore and the
    # repository never carries a committed database.
    DATABASE = str(BASE_DIR / "instance" / "campusgear.db")

    # --- Session signing -----------------------------------------------------
    # Falls back to a fixed development value; see the security note above.
    SECRET_KEY = os.environ.get(
        "CAMPUSGEAR_SECRET_KEY", "dev-only-key-replace-before-deployment"
    )

    # --- Cookie hardening (Requirement 6) ------------------------------------
    # HTTPONLY stops page JavaScript from reading the session cookie, which
    # limits what a cross-site scripting bug could steal.
    SESSION_COOKIE_HTTPONLY = True

    # SAMESITE=Lax stops the cookie from being sent on cross-site POSTs, which
    # blocks the simplest form of cross-site request forgery against the staff
    # equipment-registration form.
    SESSION_COOKIE_SAMESITE = "Lax"

    # SECURE would require HTTPS. Left off because the demo runs on
    # http://localhost; turn it on for any real deployment.
    SESSION_COOKIE_SECURE = False
