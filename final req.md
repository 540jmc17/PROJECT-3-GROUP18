# CampusGear Sprint 1 — remaining work

Team handoff, November 8. Jake’s integration branch is `sprint1`. Req 1 storage and login already work there. The Req 7 menus are on `sprint1-db-roles`. The separate `sprint1_` branch describes registration and catalog features in its README, but its pushed files omit the referenced routes and templates. The integrated catalog currently opens a placeholder.

## Cam — finish the staff menu link (Req 7)

- [ ] Ask Karim/Ahmed for the branch or commit containing their working equipment form and catalog, and the Flask **GET endpoint name** that opens the form. Share both with Jake. If the files are still local, ask them to push them.
- [ ] Once the route is available in the same app, replace the disabled **Add equipment** button in [staff_home.html](src/campusgear/presentation/templates/staff_home.html) with a link using `url_for()` and their endpoint name. Their handler owns saving the form.
- [ ] Sign in as a student and open **Browse equipment to borrow** and **My reservations & loans**. Confirm **Add equipment** is hidden. Sign in as staff and confirm **View inventory** opens the catalog and **Add equipment** opens the form. Give Jake the commit and the result. If blocked, tell Jake which file or endpoint is missing.

## Jake — integrate the remaining work

- [ ] Bring the role menus and Cam’s link into `sprint1`. Integrate Karim/Ahmed’s feature files with the existing Flask app, login, and shared SQLite database. If their files are unavailable, the two outstanding behaviors are:
  - **Req 2, registration.** A staff-only form accepts name, category, description, and unique asset ID. Its handler saves with `insert_record()`, reports success, and displays a clear duplicate-ID error. Enforce staff permission on the handler as well as the form page.
  - **Req 3, catalog.** Update the existing `/catalog` route to call `list_equipment(connection, available_only=True)`. Render the returned items and their details in the catalog template.
- [ ] On the integrated branch, run `python -m pytest`. Then do the release check below. Earlier passing tests cover storage, login, and navigation; they do not establish that the registration form saves through the website.

**Release check:** As staff, register a camera with a new asset ID. Try the same ID again and verify there is still only one camera. Restart the app using the same database, sign in as a student, and confirm the camera appears with the correct details. Check that unavailable items aren’t shown as available and a student cannot open or submit the staff form.

## Jake — submission

- [ ] Verify the README setup, seed, and startup commands from a fresh checkout. Remove temporary team handoffs and their README links before submission.
- [ ] Make sure the working release is on the branch the TA will grade. The assignment asks for the master branch URL; this repo uses `main`. Submit the agreed release URL, updated requirements stack, and Sprint 2 requirements artifacts to Canvas by **11:59 PM Sunday, November 8**.

Student reservation creation/cancellation and staff checkout/returns are Sprint 2. For Sprint 1, the student demo ends with browsing available equipment. See the [Sprint 1 acceptance criteria](docs/Sprint1_RequirementsArtifacts.md).
