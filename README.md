# CampusGear

Flask + SQLite web app for reserving and borrowing KU equipment (EECS 581 Project 3, Group 18).

This branch combines the navigation skeleton (Req 4), the SQLite storage layer (Req 1)
and login / privacy protection (Req 5 and 6). Equipment registration and the catalog
(Req 2 and 3) plug into it next.

## Run it

Python 3.10+ is required.

```bash
pip install -r requirements.txt
python3 seed.py --sample-data        # creates the database + 3 test accounts (safe to repeat)
python3 app.py                       # open http://127.0.0.1:5000
```

The database is created automatically on startup at `instance/campusgear.sqlite3`
(override with `CAMPUSGEAR_DB_PATH`). Nothing in `instance/` is committed to Git.

Optional environment variables:

| Variable | Purpose |
| --- | --- |
| `CAMPUSGEAR_SECRET_KEY` | Signs login sessions (at least 32 characters). If unset, a random key is used and logins reset on each restart. Generate one with `python3 -c "import secrets; print(secrets.token_hex(32))"`. |
| `CAMPUSGEAR_COOKIE_SECURE=1` | Send the session cookie only over HTTPS. Leave unset for `http://127.0.0.1`. |
| `CAMPUSGEAR_DB_PATH` | Use a different SQLite file. |
| `CAMPUSGEAR_ENABLE_TEST_ROUTES=1` | Turns on the throwaway `/test/*` routes used to check Req 5/6 (off by default). |

## Test accounts (local only, created by `seed.py`)

| Account | Email | Password | Role |
| --- | --- | --- | --- |
| Student A | `student.a@ku.edu` | `StudentA-pass-123` | student |
| Student B | `student.b@ku.edu` | `StudentB-pass-123` | student |
| Staff Member | `staff@ku.edu` | `Staff-pass-12345` | staff |

`python3 seed.py --reset` deletes the whole database first (it asks you to confirm).

## Verify

```bash
python3 -m pytest
```

Runs the database tests (Req 1), navigation tests (Req 4) and login/privacy tests (Req 5 and 6).
Every test uses its own temporary database.

Manual check of Req 5/6 after `python3 seed.py --sample-data`: sign in as Student A, open
"My reservations & loans" (works), then change the URL to `/students/2/records` (403 Forbidden).
Sign in as the staff member and both records pages open. A student opening `/staff` gets 403.

## Database

SQLite storage for users, equipment, reservations and loans lives in `src/campusgear/db.py`
and `src/campusgear/schema.sql`. Team integration details are in [handoff.md](handoff.md);
login/privacy integration details are in [docs/AUTH_HANDOFF.md](docs/AUTH_HANDOFF.md).
