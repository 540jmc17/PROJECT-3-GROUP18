# CampusGear — Sprint 1 Release

**Course:** EECS 581 Software Engineering II, Fall 2026 — Professor Hossein Saiedian
**Team:** Group 18
**Project:** Project 3 — Team-Generated Application
**Sprint:** 1 of 4 (Requirements 1–7, 42 story points)

CampusGear is a web application that lets KU students browse, reserve, and borrow
university equipment — lab gear, laptops, cameras, calculators, microphones — while
staff manage inventory, checkouts, returns, and maintenance.

---

## Team

| Member | Sprint 1 Requirements |
|---|---|
| Pranav Reddy, Cameren Green | 1 (database), 7 (role-specific features) |
| John, Jake Crawford | 4 (website skeleton and navigation menu) |
| Zema, Nate | 5 (login/logout), 6 (privacy and password hashing) |
| Karim Lakhani, Ahmed | 2 (equipment registration), 3 (equipment catalog) |

---

## Running the application

Requires Python 3.10 or newer.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create the database and load sample data
python seed_data.py

# 3. Start the server
python app.py
```

Then open **http://localhost:5000** in a browser.

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Staff | `avery.staff@ku.edu` | `StaffPass123` |
| Student A | `student.a@ku.edu` | `StudentPass123` |
| Student B | `student.b@ku.edu` | `StudentPass123` |

These are local demo credentials for the GTA walkthrough only. They are printed
on the login page so no separate handout is needed.

---

## Running the tests

```bash
python -m pytest -v
```

**49 tests, all passing.** The suite in `tests/test_sprint1.py` is organised so
each test class is one requirement and each test method is one numbered step from
that requirement's *Verification Steps* list in
`docs/Sprint1_RequirementsArtifacts.md`. Running with `-v` prints the mapping
directly:

```
TestRequirement1DatabaseStorage::test_step5_6_invalid_relationship_is_rejected PASSED
TestRequirement2EquipmentRegistration::test_step5_6_duplicate_asset_id_is_rejected PASSED
TestRequirement6StudentPrivacy::test_step3_4_student_cannot_access_another_students_records PASSED
...
```

Each test builds its own temporary database, so the tests can run in any order and
never touch the development database in `instance/`.

---

## Architecture

The code is organised into the three layers defined in
`docs/Software_Architecture_Document.pdf`. Each directory is one layer, so the
mapping from the design document to the source tree is one to one.

```
campusgear/
├── app.py                          Application factory, error handlers
├── config.py                       Database path, session key, cookie flags
├── seed_data.py                    Sample accounts and equipment
│
├── presentation/                   PRESENTATION LAYER  (section 3.1)
│   ├── auth_routes.py                3.1.1  Login Interface
│   ├── student_routes.py             3.1.2  Student Interface
│   └── staff_routes.py               3.1.3  Staff Interface
│
├── business_logic/                 BUSINESS LOGIC LAYER  (section 3.2)
│   ├── user_access.py                3.2.1  User and Access Management
│   ├── equipment_mgmt.py             3.2.2  Equipment Management
│   └── access_control.py             Role and ownership enforcement
│
├── data_access/                    DATA ACCESS LAYER  (section 3.3)
│   ├── database.py                   3.3.1  Data Access Component
│   └── schema.sql                    SQLite schema, all six record types
│
├── templates/                      Jinja2 HTML templates
├── static/css/style.css            Stylesheet
├── static/js/main.js               Client-side form helpers
├── tests/test_sprint1.py           49 verification tests
└── docs/                           Requirements, architecture, meeting logs
```

**Data flow.** A request enters through a route in `presentation/`, which checks
permissions and calls a function in `business_logic/`. Business logic applies the
rules and calls `data_access/database.py`, the only module that issues SQL. Results
travel back up the same path. No route writes SQL and no business-logic module
touches the session directly.

Four of the six Business Logic components are scheduled for later sprints:
Reservation Management and Loan Management in Sprint 2, Maintenance/Damage
Management in Sprint 3, and Messaging and Notifications in Sprint 4. All six
database tables already exist, so those sprints need no schema migration.

---

## Requirement traceability

| Req | Description | Points | Implemented in | Tests |
|---:|---|---:|---|---|
| 1 | Store equipment, user, reservation, and loan records | 8 | `data_access/schema.sql`, `data_access/database.py` | `TestRequirement1DatabaseStorage` |
| 2 | Staff registration of new equipment with unique asset ID | 5 | `business_logic/equipment_mgmt.py`, `presentation/staff_routes.py`, `templates/register_equipment.html` | `TestRequirement2EquipmentRegistration` |
| 3 | Equipment catalog showing available equipment | 3 | `business_logic/equipment_mgmt.py`, `presentation/student_routes.py`, `templates/catalog.html` | `TestRequirement3EquipmentCatalog` |
| 4 | Navigation menu | 2 | `templates/base.html`, `static/css/style.css` | `TestRequirement4NavigationMenu` |
| 5 | Secure login and logout | 8 | `business_logic/user_access.py`, `presentation/auth_routes.py`, `templates/login.html` | `TestRequirement5Login` |
| 6 | Protect students' private information | 13 | `business_logic/access_control.py`, `business_logic/user_access.py`, `config.py` | `TestRequirement6StudentPrivacy` |
| 7 | Role-specific website features | 3 | `business_logic/access_control.py`, `templates/base.html`, all three route modules | `TestRequirement7RoleSpecificFeatures` |
| | **Total** | **42** | | |

---

## How Requirement 6 is enforced

Requirement 6 is the largest item in the sprint at 13 points, so it is worth
stating precisely what protects what.

1. **Passwords are never stored.** `user_access.create_user` stores only a
   PBKDF2-SHA256 hash with a per-user random salt, produced by
   `werkzeug.security.generate_password_hash`. Two accounts with the same password
   get different hashes, and a test asserts this.

2. **Permission checks run in the backend, not the template.** Every staff route
   carries `@staff_required`. Hiding a link in the navigation menu is convenience
   only — a student who types `/staff/dashboard` directly still receives 403. A
   test asserts exactly this case.

3. **Ownership is checked before data is loaded.** `require_self_or_staff` runs at
   the top of `student_records`, before the record is read, so a denied request
   never touches the data it was not allowed to see.

4. **Login reveals nothing.** A wrong password and a nonexistent account produce
   the identical message, so the form cannot be used to discover which email
   addresses have accounts.

5. **All queries are parameterised.** `data_access/database.py` takes SQL and
   parameters separately; no query in the application is built by string
   concatenation. Two tests confirm that classic injection payloads fail safely.

6. **Session cookies are hardened.** `HTTPONLY` and `SAMESITE=Lax` are set in
   `config.py`. `SECURE` is off only because the demo runs over HTTP on localhost.

---

## Suggested GTA demo sequence

1. `python seed_data.py && python app.py`, open http://localhost:5000 — redirects
   to login **(Req 5)**.
2. Log in as staff — lands on the Staff Dashboard, header shows the STAFF badge
   **(Req 7)**.
3. Walk the navigation menu: Home, Catalog, Dashboard, Register Equipment
   **(Req 4)**.
4. Register a new item, for example asset `KU-CAM-003` — a confirmation appears
   and the item shows on the dashboard **(Req 2)**.
5. Submit the same asset ID again — rejected as a duplicate **(Req 2)**.
6. Log out, log in as Student A — the menu now has no staff links **(Req 7)**.
7. Open the catalog — the item registered in step 4 is listed **(Req 3)**.
8. Type `/staff/dashboard` into the address bar — access denied, 403 **(Req 6)**.
9. Open `/students/2/records`, then change the URL to `/students/3/records` —
   access denied **(Req 6)**.
10. Stop the server, restart it, log back in — the data is still there **(Req 1)**.
11. Run `python -m pytest -v` — 49 tests pass, named after the verification steps.

---

## Known limitations

These are scope boundaries, not defects. Each is scheduled.

- Reserving equipment is not implemented; the catalog is read-only in Sprint 1.
  Reservations are Requirements 8–10 in Sprint 2.
- The `maintenance_tickets` and `damage_reports` tables exist but have no user
  interface yet (Requirements 19 and 22, Sprint 3).
- There is no public sign-up page. Accounts are created by `seed_data.py`, which
  matches a system where KU provisions accounts rather than students registering
  themselves.
- `SECRET_KEY` has a development default in `config.py`. Set the
  `CAMPUSGEAR_SECRET_KEY` environment variable for any real deployment.

---

## Source attribution

Per the course policy on source attribution, every file in this repository carries
a prologue comment naming its external sources. Summarised here:

- **Claude (Anthropic)** was used throughout to draft code, comments, and
  documentation from the team's Software Architecture Document and Sprint 1
  Requirements Artifacts. Every file's prologue names it. All output was reviewed
  and tested by the team before commit.
- **Flask documentation** — application factory, blueprints, the
  application-context database pattern, flash messages, and testing patterns.
  <https://flask.palletsprojects.com/>
- **Werkzeug documentation** — `generate_password_hash` and `check_password_hash`.
  <https://werkzeug.palletsprojects.com/>
- **SQLite documentation** — `CREATE TABLE`, CHECK and UNIQUE constraints, and
  foreign-key enforcement. <https://www.sqlite.org/>
- **MDN Web Docs** — `HTMLFormElement` and `classList` APIs used in `main.js`.
- **KU brand guidelines** — Jayhawk Blue `#0051BA` and Crimson `#E8000D`.

---

## Documents in `docs/`

| File | Contents |
|---|---|
| `Project_3_Requirements.xlsx` | Updated requirements stack — all 40 requirements assigned to sprints, plus a Sprint_Summary sheet |
| `Sprint1_RequirementsArtifacts.md` | Sprint 1 plan and per-requirement artifacts (delivered) |
| `Sprint2_RequirementsArtifacts.md` | Sprint 2 plan and per-requirement artifacts (next sprint) |
| `Sprint1_Demo_Script.md` | Step-by-step GTA demo walkthrough mapped to requirements |
| `Software_Architecture_Document.pdf` | Three-layer architecture, component/class/sequence/use-case diagrams |
| `Team18_Meeting_Log_1.pdf` | Meeting log |

### Sprint plan at a glance

| Sprint | Requirements | Count | Points | Status |
|---:|---|---:|---:|---|
| 1 | 1–7 | 7 | 42 | Delivered |
| 2 | 8, 9, 10, 11, 13, 15, 16, 20, 21, 25 | 10 | 41 | Planned |
| 3 | 12, 14, 17, 18, 19, 22, 23, 24, 26, 27, 29, 30 | 12 | 54 | Forecast |
| 4 | 28, 31–40 | 11 | 52 | Forecast |
| | **Total** | **40** | **189** | |

Sprint 2 is committed at 41 points against the 42 delivered in Sprint 1, so the
plan matches demonstrated velocity rather than exceeding it.
