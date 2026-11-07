# CampusGear — Requirement 1 database

SQLite storage for users, equipment, reservations, and loans.
Use Python 3.10+ from the repository folder. No additional packages are needed.

Create the application database:

```bash
python3 -c "from campusgear.db import initialize; initialize()"
```

Run the checks and sample demo:

```bash
python3 -m unittest discover -s tests -p test_db.py -v
python3 -m campusgear.demo
```

Application data is stored locally in `instance/campusgear.sqlite3`.
The demo creates a separate sample database and prints its path for DB Browser.
Database files are not committed to Git.

This contribution contains the database only; website and login integration follow
separately. Team integration details are in [handoff.md](handoff.md).
