/*
 * Module Name: schema.sql
 * Description: Defines the users, equipment, reservations, and loans tables.
 *
 * Inputs: SQLite schema initialization and subsequent record writes.
 * Outputs: Four tables with required fields and relationship constraints.
 *
 * Implementation authors: Pranav Reddy and Cameren Green, with Codex drafting assistance.
 * Creation Date: November 3, 2026.
 * Reviewed by: Pranav Reddy and Cameren Green. Schema accepted; readability changes requested.
 * Documentation author: Pranav Reddy, with assistance from OpenAI Codex.
 * External Sources / Attribution: Created with assistance from OpenAI Codex.
 * Uses standard SQLite table definitions and constraints.
 * Code Origin: Newly written for EECS 581 Project 3, Requirement 1.
 *
 */

-- IF NOT EXISTS makes initialization safe to repeat; it does not alter old tables.
-- INTEGER PRIMARY KEY assigns an ID when an INSERT leaves it out.
-- NOT NULL requires a value. CHECK rejects values that break its rule.
-- trim(value) <> '' rejects empty text and text containing only spaces.
-- Account hashes are generated/checked by the login team. Roles are stored here.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (trim(name) <> ''),
    -- UNIQUE prevents duplicate emails; NOCASE ignores letter casing.
    email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (trim(email) <> ''),
    -- Store the hash supplied by the login team, never the plain password.
    password_hash TEXT NOT NULL CHECK (trim(password_hash) <> ''),
    role TEXT NOT NULL CHECK (role IN ('student', 'staff'))
);

-- Each row represents one physical item or complete kit; asset_id is its label.
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY,
    asset_id TEXT NOT NULL UNIQUE CHECK (trim(asset_id) <> ''),
    name TEXT NOT NULL CHECK (trim(name) <> ''),
    category TEXT NOT NULL CHECK (trim(category) <> ''),
    description TEXT NOT NULL,
    condition TEXT NOT NULL DEFAULT 'good' CHECK (trim(condition) <> ''),
    -- DEFAULT supplies a value if omitted; IN limits the allowed choices.
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'reserved', 'checked_out', 'maintenance'))
);

-- A reservation records the plan to borrow an item.
-- Dates use YYYY-MM-DD, so comparing their text also compares their dates.
-- date(value, '+0 days') normalizes a date; comparing it with the original
-- rejects impossible dates such as February 30. IS also rejects a NULL result:
-- using = alone could let an unparseable date pass SQLite's CHECK.
-- The length check requires the ten-character date format.
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY,
    -- REFERENCES requires an existing user/item. RESTRICT prevents deleting
    -- that parent record while this record still refers to it.
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE RESTRICT,
    pickup_date TEXT NOT NULL CHECK (
        length(pickup_date) = 10 AND date(pickup_date, '+0 days') IS pickup_date),
    return_date TEXT NOT NULL CHECK (
        length(return_date) = 10 AND date(return_date, '+0 days') IS return_date
        AND return_date > pickup_date),
    status TEXT NOT NULL DEFAULT 'reserved'
        CHECK (status IN ('reserved', 'checked_out', 'cancelled', 'completed')),
    -- Automatically record creation time in UTC; Z means UTC.
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    -- SQLite needs this UNIQUE group for the three-column reference below.
    UNIQUE (id, user_id, equipment_id)
);

-- A loan always names its borrower/item. Its optional reservation supports Req 12
-- walk-ins; the composite reference prevents linking a different borrower/item.
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY,
    -- REFERENCES requires an existing user/item. RESTRICT prevents deleting
    -- that parent record while this record still refers to it.
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE RESTRICT,
    -- NULL means no reservation (a walk-in). UNIQUE allows at most one loan
    -- per reservation, while SQLite still permits multiple NULL values.
    reservation_id INTEGER UNIQUE,
    checkout_date TEXT NOT NULL CHECK (
        length(checkout_date) = 10 AND date(checkout_date, '+0 days') IS checkout_date),
    due_date TEXT NOT NULL CHECK (
        length(due_date) = 10 AND date(due_date, '+0 days') IS due_date
        AND due_date > checkout_date),
    -- Leave this NULL until return; a return cannot precede checkout.
    actual_return_date TEXT CHECK (actual_return_date IS NULL OR (
        length(actual_return_date) = 10
        AND date(actual_return_date, '+0 days') IS actual_return_date
        AND actual_return_date >= checkout_date)),
    status TEXT NOT NULL DEFAULT 'checked_out'
        CHECK (status IN ('checked_out', 'returned')),
    -- A recorded return and the loan status must agree.
    CHECK ((status = 'returned' AND actual_return_date IS NOT NULL)
        OR (status = 'checked_out' AND actual_return_date IS NULL)),
    -- All three values must match the SAME reservation row, preventing a
    -- loan from linking to someone else's reservation or a different item.
    -- When reservation_id is NULL, this group check is skipped; the separate
    -- user/item references above still apply.
    FOREIGN KEY (reservation_id, user_id, equipment_id)
        REFERENCES reservations(id, user_id, equipment_id) ON DELETE RESTRICT
);
