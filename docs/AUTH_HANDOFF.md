# CampusGear: Login and Privacy Hand-Off (Req 5 and 6)

Owner: Zema Samuel. Temporary team document: remove before final submission.

Login is a drop-in gateway. You never handle passwords or sessions: import a decorator,
read two session keys.

## 1. Session keys (read only)

| Key | Value |
| --- | --- |
| `session["user_id"]` | integer `users.id` of the signed-in user |
| `session["role"]` | `"student"` or `"staff"` |

Also set: `session["name"]` (display name) and `session["_csrf_token"]` (internal).
Signed out means these keys are absent. Never take a student's identity from a form or URL; use the session.

In any template (Req 7): `current_user` is `None` when signed out, otherwise a dict with
`id`, `role` and `name`. Example: `{% if current_user and current_user.role == "staff" %} ... {% endif %}`.
In Python: `from campusgear.business_logic.user_access import current_user`.

## 2. Decorators

```python
from campusgear.business_logic.user_access import (
    login_required, role_required, owner_or_staff_required)
```

Put them **below** `@bp.route(...)`.

| Decorator | Allows | Otherwise |
| --- | --- | --- |
| `@login_required` | any signed-in user | redirect to `/login` |
| `@role_required("staff")` or `("student")` | that role only | signed out: redirect to `/login`; wrong role: 403 |
| `@owner_or_staff_required("student_id")` (bare `@owner_or_staff_required` also works) | any staff, or the student whose `id` equals the URL parameter | signed out: redirect; another student: 403 |

```python
@bp.route("/equipment/new", methods=["GET", "POST"])
@role_required("staff")                     # Req 2: staff-only registration
def register_equipment(): ...

@bp.route("/students/<int:student_id>/loans")
@owner_or_staff_required("student_id")      # URL parameter name must match
def student_loans(student_id): ...
```

Also use the check on POST handlers. Hiding a button is not security.

## 3. Routes and endpoint names

| Endpoint | URL | Notes |
| --- | --- | --- |
| `auth.login` | `/login` | GET form, POST `email` + `password` + `csrf_token` |
| `auth.logout` | `/logout` | **POST only**, needs `csrf_token` |
| `student.student_home` | `/student` | students only (placeholder page for Req 7) |
| `staff.staff_home` | `/staff` | staff only (placeholder page for Req 7) |
| `student.student_records` | `/students/<id>/records` | owner or staff: a student's reservations and loans |

Login result: student goes to `/student`, staff to `/staff`. Every failure shows one message,
"Invalid credentials" (HTTP 401). The menu in `base.html` already shows "Sign in" or the user's
name plus a "Log out" button. Other POST forms are not CSRF-checked automatically. To protect one the same way, include
`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` and call `csrf_is_valid()` (from `user_access`) in the handler.

Real private-record data is read with ownership filters in `get_student_records()`
(`business_logic/user_access.py`); the Req 10 and 26 owners can move or extend it.

## 4. For specific owners

- **Karim/Ahmed (Req 2, 3):** protect equipment registration with `@role_required("staff")` before calling
  `insert_record`. The catalog is public for now (`site.catalog`); if it should require login, add `@login_required`.
- **Jake/John (Req 4):** the old `site.login` placeholder was removed (the `/login` route now lives in
  `presentation/login.py`). `base.html` and `home.html` use `url_for('auth.login')`.
- **Pranav/Cameren (Req 1, 7):** the app sets `app.config["DATABASE"]` and runs `initialize()` at startup, as your handoff
  suggested. Users are created through `create_account()` (uses your `insert_record`). If the `users` table or a column is renamed, update
  `DB_SCHEMA` in `src/campusgear/config.py` (login queries) **and** `FIELDS["users"]` in `db.py` (your write helper).
  Req 7 can read `current_user.role` in the layout.
- **Everyone:** `tests/test_auth.py::test_every_non_public_route_blocks_anonymous_users` fails if you add a page that anonymous
  visitors can open. If a page is meant to be public, add its endpoint to `PUBLIC_ENDPOINTS` in that test.

## 5. Cleanup before final submission

Delete `src/campusgear/presentation/auth_test_routes.py` (and its registration in `__init__.py`), the
`/test/*` tests in `tests/test_auth.py`, and this document. `seed.py` may stay as the TA test-account setup.
