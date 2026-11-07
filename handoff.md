# CampusGear — Req 1 database handoff

For Pranav/Cameren, Karim/Ahmed, Jake/John, and Zema/Nate. Updated November 5, 2026.

Temporary team communication document: remove before final submission and remove
its README link. Keep the final application setup instructions in README.md.


> **Layout note (combined branch):** the database files now live in `src/campusgear/`
> (`db.py`, `schema.sql`, `demo.py`) next to the Flask app, so imports such as
> `from campusgear.db import ...` are unchanged. Run commands from the repo root with
> `python3 -m pytest`; the demo is `cd src && python3 -m campusgear.demo`. The app now sets
> `app.config['DATABASE']` and calls `initialize()` at startup. Login/privacy details are in
> `docs/AUTH_HANDOFF.md`.

## Scope and ownership

This handoff describes the Python interface prepared on `sprint1-db-roles`.
The shared integration target is `sprint-1`. This contribution implements Req 1
only. It contains no Flask app, frontend, login, or Req 7 role-display implementation.

| Requirement | Owners | What our layer supplies | What the feature owners implement |
| --- | --- | --- | --- |
| 1 — Database storage | Pranav/Cameren | Four tables, initialization, transactions, save/read helpers, sample records and checks | Coordinate the shared database path and schema changes |
| 2 — Equipment registration | Karim/Ahmed | Equipment fields, insert helper, uniqueness constraints | Form, Flask handler, input validation, staff authorization, success/error display |
| 3 — Equipment catalog | Karim/Ahmed | Equipment-list helper and single-item reads | Flask handler and catalog rendering with correct availability |
| 4 — Skeleton/navigation | Jake/John | Database setup instructions and Python imports | Shared Flask application, layout, navigation and route names |
| 5 — Login/logout | Zema/Nate | User storage, role/password_hash columns, connection for account lookup | Account provisioning, hashing/verification, login/logout, session handling |
| 6 — Privacy/access | Zema/Nate | User IDs and record relationships for ownership checks | Server-side authentication, authorization, private-record filtering and safe responses |
| 7 — Role-specific display | Pranav/Cameren | Stored user role only; UI work is separate | Integrate with the shared layout and authenticated role supplied by the login team |

## Connection map — Cam and the feature teams

The browser never calls SQLite or imports Python. The full flow is:

`HTML form/page → feature team's Flask handler → db.py → SQLite file`

- Karim/Ahmed connect their equipment form to a Flask POST handler. That handler
  validates the fields and calls `insert_record()` inside `transaction()`.
- Their catalog GET handler calls `list_equipment()` and passes the resulting
  dictionaries to the catalog template for display.
- Zema/Nate connect their login form to their login handler, query the stored user,
  verify the password hash, and establish the authenticated user ID and role.
- Jake/John's navigation links to those feature routes in the shared Flask app.
- Pranav/Cam supply the database files and help everyone use the same database path.
  Later Req 7 work connects the authenticated role to options in the shared layout.

Nothing automatically wires a form to these functions. Feature owners write those
handlers. Before integrating, share route names and the authenticated-user access
convention with Pranav/Cam. No extra layout work is needed from Jake/John now.

## Shared database setup — everyone

Keep `campusgear/db.py`, `campusgear/schema.sql`, and `campusgear/__init__.py`
together in the shared project. Python's built-in `sqlite3` library handles storage.
Req 1 needs no third-party dependencies. The website team manages Flask dependencies.

Initialize the application database once during setup:

```python
from campusgear.db import initialize
initialize()
```

The default is `instance/campusgear.sqlite3` under the directory containing the
`campusgear` package. Its location is independent of the terminal working directory.
All feature handlers must use the same file. If the shared Flask application chooses
another location, pass that identical path to `initialize(path)` and every
`transaction(path)` call. For example, the shared application may define
`app.config['DATABASE']` and handlers use `transaction(current_app.config['DATABASE'])`.
That configuration key is an integration convention to agree on, not an existing
setting supplied by this database module.

Initialization creates empty tables and preserves existing rows. Schema changes to
existing tables require a coordinated migration. The terminal demo creates separate
`instance/demo-....sqlite3` files. Its sample users have disabled placeholder hashes.
Prepare real test accounts through the login team's account-creation code.

## Exact Python interface

```python
from campusgear.db import (
    DEFAULT_PATH, initialize, transaction,
    insert_record, get_record, list_equipment,
)
```

| Function | Result and behavior |
| --- | --- |
| `initialize(path=DEFAULT_PATH)` | Creates missing tables in the chosen file |
| `transaction(path=DEFAULT_PATH)` | Context manager yielding a SQLite connection with foreign keys enabled |
| `insert_record(connection, table, **fields)` | Saves one row and returns its numeric ID; the enclosing transaction commits it |
| `get_record(connection, table, record_id)` | Returns a dictionary for the ID, or `None` |
| `list_equipment(connection, available_only=False)` | Returns equipment dictionaries ordered by ID; `True` filters status to `available` |

```python
with transaction() as connection:
    item = get_record(connection, 'equipment', 1)
```

Each transaction opens and closes its own connection. Successful exit commits all
writes. An exception leaving the block rolls back the writes. Catch write errors
outside the `with` block so rollback can occur. SQL values use placeholders.
Choose table and field names in backend code rather than accepting them from a form.

- `sqlite3.IntegrityError` indicates a violated constraint, such as duplicate asset
  ID, missing required value, invalid date, or missing referenced record.
- `ValueError` indicates an unknown table/field name or an empty insert request.
- Other SQLite errors can indicate a locked file or storage/configuration failure.

Handlers should report an appropriate error. Treating every database failure as a
duplicate or successful save would hide the actual issue.

## Requirement 2 — Karim/Ahmed equipment registration

The equipment form sends these fields to your Flask handler:

| Field | Storage rule |
| --- | --- |
| `name` | Required, nonblank text |
| `category` | Required, nonblank text |
| `description` | Required text; the database permits an empty string, so validate useful content in the form/handler |
| `asset_id` | Required, nonblank, unique inventory label |
| `condition` | Optional on insert, defaults to `good` |
| `status` | Optional on insert, defaults to `available` |

SQLite assigns `id`. Use that numeric ID for relationships. `asset_id` is the label
staff enter. Asset labels are currently case-sensitive. Trim inputs and agree on
label capitalization if the team wants a consistent convention.

After checking the input and the caller's staff permission, your handler calls:

```python
with transaction() as connection:
    item_id = insert_record(
        connection, 'equipment', name=name, category=category,
        description=description, asset_id=asset_id,
    )
```

Here the variables represent validated form values. Catch `sqlite3.IntegrityError`
outside the block. A duplicate asset ID should produce a clear form error. On
success, redirect to the catalog or show the saved item.

Integration check: add an item, retrieve it from the catalog, then attempt its asset
ID again and verify that no additional row is created.

## Requirement 3 — Karim/Ahmed equipment catalog

```python
with transaction() as connection:
    equipment = list_equipment(connection, available_only=True)
```

Pass `equipment` to your HTML template. Each dictionary contains `id`, `asset_id`,
`name`, `category`, `description`, `condition`, and `status`. An empty catalog is
an empty list. Use `get_record(connection, 'equipment', item_id)` for one item and
handle `None` as a missing item.

To show all items with their availability, omit the filter and display each stored
status correctly. Allowed equipment statuses are `available`, `reserved`,
`checked_out`, and `maintenance`. This helper reads current status. Future date
conflicts and reservation availability need reservation business logic.

Send Pranav/Cam the form/catalog route names and branch/files when ready so the
role-specific links can target the actual pages.

## Requirement 4 — Jake/John skeleton and navigation

Use the shared Flask application and agree on route names with the equipment and
login teams. Navigation links target their routes, not database functions.

No additional UI work is requested now. When integration starts, share the app
entry point, layout/template locations, route names, and run command with
Pranav/Cam. Run database initialization once as a setup step.

## Requirement 5 — Zema/Nate login, accounts and password hashing

The `users` table contains these fields:

| Field | Storage rule |
| --- | --- |
| `id` | Assigned numeric ID |
| `name` | Required nonblank text |
| `email` | Required nonblank text, case-insensitively unique |
| `password_hash` | Required nonblank text containing the hashing library's full encoded output |
| `role` | Exactly `student` or `staff` |

The login team chooses and owns the password hashing and verification library.
Use its hash-generation function during account creation and its password-check
function during login. Store the full returned hash string, including the metadata
that library encodes. Password hashing and email-format validation happen before
storage. The database only checks that these strings are nonempty.

```python
# hashed_password comes from the login team's password-hashing function.
with transaction() as connection:
    user_id = insert_record(
        connection, 'users', name=name, email=email,
        password_hash=hashed_password, role='student',
    )
```

Staff accounts must be provisioned through a trusted path. Never accept staff
privileges from an untrusted form field or URL parameter.

There is currently no dedicated email-lookup helper. Your login code can use this
parameterized query through the existing connection:

```python
with transaction() as connection:
    user = connection.execute(
        'SELECT id, name, email, password_hash, role FROM users WHERE email = ?',
        (email.strip(),),
    ).fetchone()
```

`user` is a `sqlite3.Row` or `None`. Check for `None`, then use the library's
password-verification function with `user['password_hash']`. The email column's
collation supplies case-insensitive matching. After successful authentication,
your session code records the trusted user ID and makes the account role available
to routes/templates. Logout and protected-route checks belong to this team.

Never expose `password_hash` in rendered pages, JSON responses, logs, or session
payloads. `get_record(connection, 'users', user_id)` includes this column, so choose
public response fields explicitly.

Needed agreement with Pranav/Cam: how a route gets the authenticated user ID and
role, how test accounts are created, and which hashing/verification functions are
used. Proposed simple template value: `role` containing `student` or `staff`.

## Requirement 6 — Zema/Nate privacy and permissions

Foreign keys enforce record relationships. Your backend must additionally check
whether the requesting account may read or change each record. A real student's
ID must come from the authenticated session.

For example, an ownership-filtered reservation read can use:

```python
with transaction() as connection:
    reservation = connection.execute(
        'SELECT * FROM reservations WHERE id = ? AND user_id = ?',
        (reservation_id, authenticated_user_id),
    ).fetchone()
```

Apply equivalent ownership checks to loans, which also have `user_id`. Deny a
missing/unauthorized result appropriately. Authorize staff-only actions before
calling the equipment write helper. Hiding an option in a template is only the
visible part of role handling.

Integration checks should cover Student A requesting Student B's records, a
student calling the staff equipment endpoint directly, and logged-out requests
to protected pages. The generic database helpers provide storage access to trusted
backend callers and perform no request-level authorization themselves.

## Requirement 7 — later work, outside this push

The database stores `users.role` as `student` or `staff`. Pranav/Cam will later use
the authenticated role from Zema/Nate to show the correct options in Jake/John's
layout and link to Karim/Ahmed's routes. That UI is not included here. Backend
handlers must enforce permissions independently of which options are visible.

## Reservation and loan storage reference

These tables already exist for Req 1. Later feature owners can use `insert_record`
and `get_record` with the following names.

| Table | Required insert fields | Optional/default fields |
| --- | --- | --- |
| `reservations` | `user_id`, `equipment_id`, `pickup_date`, `return_date` | `status='reserved'`; SQLite generates UTC `created_at` |
| `loans` | `user_id`, `equipment_id`, `checkout_date`, `due_date` | `reservation_id=NULL`, `actual_return_date=NULL`, `status='checked_out'` |

- Dates use `YYYY-MM-DD` and must be real calendar dates. Reservation return date
  must follow pickup date. Loan due date must follow checkout date.
- Reservation statuses are `reserved`, `checked_out`, `cancelled`, `completed`.
- Loan statuses are `checked_out`, `returned`. A returned loan requires an actual
  return date on or after checkout. A checked-out loan requires a NULL return date.
- User/item references must exist. Referenced parent records cannot be deleted.
- A linked reservation must match the loan's user/item and can have at most one loan.
  An optional reservation supports backlog Req 12 walk-ins. This decision needs to
  be reflected when the team updates the original reservation-only architecture.
- Inserting a record does not update other tables' statuses. Future checkout/return
  handlers must perform the related writes together in a transaction.
- The schema does not prevent overlapping bookings or verify that a referenced
  user has the student role. Those checks belong to the relevant business logic.
- Generic update/delete helpers, maintenance, messaging and waitlist storage are
  outside this handoff's implemented interface. Coordinate additions before use.

## Verification and later TA README

From the repository folder with Python 3.10+ (no package installation needed):

```bash
python3 -m unittest discover -s tests -p test_db.py -v
python3 -m campusgear.demo
```

The terminal demo prints its separate database path and verifies save/retrieve,
persistence in a fresh Python process, and rejection of an invalid relationship.
The demo does not populate the application database or create usable login accounts.

When the combined application is ready, its TA README needs the shared dependency
installation command, one DB initialization command, test-account setup, the actual
Flask startup command/URL, and the equipment/role verification steps. Pranav/Cam
will supply the database instructions above. Verify persistence after restarting
that combined application using the same database path.
