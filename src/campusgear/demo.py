"""
Module Name: demo.py
Description: Demonstrates Req 1 storage, persistence, and invalid-reference rejection.

Inputs: Sample records and an optional --verify database path.
Outputs: A sample SQLite file and printed verification results.

Implementation author: Pranav Reddy, with assistance from OpenAI Codex.
Creation Date: November 3, 2026.
Reviewed by: Pranav Reddy and Cameren Green. Approved for inclusion; demo checks passing.
Documentation author: Pranav Reddy, with assistance from OpenAI Codex.
External Sources / Attribution: Created with assistance from OpenAI Codex.
Uses standard Python and SQLite APIs.
Code Origin: Newly written for EECS 581 Project 3, Requirement 1.

Demo implementation attribution: GPT Sol 6.1, as requested by Pranav.
Sample password hashes are disabled placeholders, not login credentials.
"""

import argparse
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

from .db import DEFAULT_PATH, initialize, transaction, insert_record, get_record


def seed(path):
    """Save one user, item, reservation, and loan in a new sample database."""
    initialize(path)
    with transaction(path) as connection:
        # Save the user and item first; the other records reference their IDs.
        student = insert_record(connection, 'users', name='Alex Morgan',
                                email='alex.morgan@example.invalid',
                                password_hash='!demo-login-disabled', role='student')
        item = insert_record(connection, 'equipment', asset_id='KU-001',
                             name='Raspberry Pi Kit', category='Lab gear',
                             description='Raspberry Pi with power supply and cables.',
                             status='checked_out')
        # The reservation is the plan; the loan records the actual pickup.
        reservation = insert_record(connection, 'reservations', user_id=student,
                                    equipment_id=item, pickup_date='2026-11-03',
                                    return_date='2026-11-10', status='checked_out')
        insert_record(connection, 'loans', user_id=student, equipment_id=item,
                      reservation_id=reservation, checkout_date='2026-11-03',
                      due_date='2026-11-10')


def verify(path):
    """Read committed records in a fresh process and exercise reference checks."""
    with transaction(path) as connection:
        assert get_record(connection, 'users', 1)['role'] == 'student'
        assert get_record(connection, 'equipment', 1)['asset_id'] == 'KU-001'
        assert get_record(connection, 'reservations', 1)['user_id'] == 1
        assert get_record(connection, 'loans', 1)['reservation_id'] == 1
        # Deliberately reference a missing user; accepting this row must fail the demo.
        try:
            insert_record(connection, 'reservations', user_id=999999, equipment_id=1,
                          pickup_date='2026-11-04', return_date='2026-11-05')
        except sqlite3.IntegrityError:
            pass  # Expected: the referenced user does not exist.
        else:
            raise AssertionError('Invalid user relationship was accepted')
    print(f'Database: {path.resolve()}')
    print('PASS: saved and retrieved all four record types')
    print('PASS: records remain after the writer closes (read in a new process)')
    print('PASS: reservation for nonexistent user rejected')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path, help='Verify an existing demo database')
    args = parser.parse_args()
    if args.verify:
        verify(args.verify)
    else:
        path = DEFAULT_PATH.parent / f'demo-{uuid4().hex}.sqlite3'
        seed(path)
        # The writer's connections are closed before a new interpreter reads.
        subprocess.run([sys.executable, '-m', 'campusgear.demo', '--verify', str(path)],
                       check=True, cwd=Path(__file__).resolve().parent.parent)


if __name__ == '__main__':
    main()
