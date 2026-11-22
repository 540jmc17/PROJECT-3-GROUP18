"""
Module Name: equipment_management.py
Description: Equipment Management component (Business Logic Layer).
             Registers new equipment (Requirement 2) and returns the
             equipment catalog (Requirement 3). Uses the Data Access helpers
             in db.py; never builds SQL from user input.
Inputs: Equipment name, category, description, and unique asset ID.
Outputs: Saved equipment ID, or a list of equipment dictionaries.
Implementation Author: Ahmed (Mado) Gharib, with substantial code-drafting assistance from Claude (Anthropic).
Creation Date: November 8, 2026.
Reviewed by: Ahmed Gharib.
Documentation Author: Ahmed Gharib, with assistance from Claude.
External Sources / Attribution: Created with assistance from Claude (Anthropic). Uses standard Flask, Jinja, and SQLite functionality.
Code Origin: Newly written for EECS 581 Project 3, Requirements 2 and 3.
Errors: EquipmentError is raised for missing fields or a duplicate asset ID.
"""

import sqlite3

from flask import current_app

from ..db import insert_record, list_equipment, transaction

REQUIRED_FIELDS = ("name", "category", "description", "asset_id")
MAX_LENGTH = 200


class EquipmentError(ValueError):
    """Raised when equipment registration input is invalid."""


def _db_path():
    return current_app.config["DATABASE"]


def clean_form(form):
    """Strip whitespace and check that every required field is filled in."""
    data = {field: (form.get(field) or "").strip() for field in REQUIRED_FIELDS}
    missing = [field.replace("_", " ") for field, value in data.items() if not value]
    if missing:
        raise EquipmentError("Please fill in: " + ", ".join(missing) + ".")
    if any(len(value) > MAX_LENGTH for key, value in data.items() if key != "description"):
        raise EquipmentError(f"Name, category, and asset ID must be under {MAX_LENGTH} characters.")
    return data


def register_equipment(form):
    """Save a new available equipment item and return its database ID."""
    data = clean_form(form)
    try:
        with transaction(_db_path()) as connection:
            return insert_record(connection, "equipment", status="available", **data)
    except sqlite3.IntegrityError as err:
        # The UNIQUE constraint on asset_id rejects duplicates.
        if "asset_id" in str(err):
            raise EquipmentError(
                f"Asset ID {data['asset_id']} is already registered. Use a unique asset ID.") from err
        raise


def get_catalog():
    """Return all equipment so the catalog can show each item's real status."""
    with transaction(_db_path()) as connection:
        return list_equipment(connection)
