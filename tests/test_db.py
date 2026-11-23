"""
Module Name: test_db.py
Description: Checks Req 1 storage, restart persistence, and invalid references.

Inputs: Sample records in a temporary SQLite database.
Outputs: Passing or failing unittest results.

Implementation author: OpenAI Codex.
Creation Date: November 3, 2026.
Reviewed by: Pranav Reddy, to confirm the tests cover the intended Req 1
implementation scope: storage/retrieval, persistence, invalid relationships,
and the equipment catalog helper.
Documentation author: Pranav Reddy, with assistance from OpenAI Codex.
External Sources / Attribution: Created with assistance from OpenAI Codex.
Uses standard Python and SQLite APIs.
Code Origin: Newly written for EECS 581 Project 3, Requirement 1.

"""

from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from campusgear.db import transaction, insert_record, get_record, list_equipment
from campusgear.demo import seed


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        # Give each test its own database containing the four sample records.
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.sqlite3'
        seed(self.path)

    def test_saved_records_survive_restart(self):
        # A new Python process reads what seed saved and checks an invalid reference.
        subprocess.run([sys.executable, '-m', 'campusgear.demo', '--verify', str(self.path)],
                       check=True, capture_output=True, text=True,
                       cwd=Path(__file__).resolve().parent.parent / 'src')  # package lives in src/

    def test_invalid_relationships_are_rejected(self):
        # Try a missing user, then a missing item, with otherwise valid data.
        for user_id, equipment_id in [(999, 1), (1, 999)]:
            with self.subTest(user_id=user_id, equipment_id=equipment_id):
                with self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY'):
                    with transaction(self.path) as connection:
                        insert_record(connection, 'reservations', user_id=user_id,
                                      equipment_id=equipment_id,
                                      pickup_date='2026-11-04', return_date='2026-11-05')
        # The rejected attempts must not leave extra rows behind.
        with transaction(self.path) as connection:
            self.assertIsNone(get_record(connection, 'reservations', 2))

    def test_save_equipment_and_read_catalog(self):
        # This is the same save/read flow the equipment team's Flask code will use.
        with transaction(self.path) as connection:
            item_id = insert_record(connection, 'equipment', asset_id='KU-002',
                                    name='Camera', category='Photography', description='Camera kit')
        with transaction(self.path) as connection:
            available = list_equipment(connection, available_only=True)
            self.assertEqual(len(list_equipment(connection)), 2)
            self.assertEqual([item['id'] for item in available], [item_id])
            self.assertEqual(available[0]['name'], 'Camera')


if __name__ == '__main__':
    unittest.main()
