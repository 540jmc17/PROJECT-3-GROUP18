# CampusGear — Sprint 1 Plan and Requirements Artifacts

## Sprint Overview

- **Sprint:** 1 of 4
- **Length:** 2 weeks
- **Total backlog:** 189 story points
- **Sprint 1 commitment:** **42 story points** across Requirements 1–7

## Sprint 1 Goal

Create a working starting version of CampusGear where staff can log in and register equipment, students can log in and browse available equipment, users can navigate the implemented pages, and backend access controls prevent unauthorized access to protected features and private data.

## Selected Requirements

| ID | Requirement | Points | Priority | Sprint |
|---:|---|---:|---:|---:|
| 1 | Store equipment, user, reservation, and loan records in a database. | 8 | 1 | 1 |
| 2 | Staff registration for new equipment by entering name, category, description, and unique asset ID. | 5 | 2 | 1 |
| 3 | Display an equipment catalog showing available equipment. | 3 | 3 | 1 |
| 4 | Display a navigation menu that allows users to access main sections of the website. | 2 | 4 | 1 |
| 5 | Allow students and staff to securely log in and log out using their accounts. | 8 | 5 | 1 |
| 6 | Protect students' private information by restricting access to unauthorized users. | 13 | 6 | 1 |
| 7 | Display different website features depending on the user's role. Students should see borrowing and reservation options, while staff should see equipment management options. | 3 | 7 | 1 |
| | **Total** | **42** | | |

---

# Sprint 1 Requirements Artifacts

## Requirement 1 — Database Storage

**Story Points:** 8

### Description
Store equipment, user, reservation, and loan information in the SQLite database so the information remains saved.

### Inputs
- User information
- Equipment information
- Reservation records
- Loan records

### Expected Output
- Information is successfully saved.
- Saved information can be retrieved.
- Information remains saved after restarting the application.

### Acceptance Criteria
- The database stores all four types of records.
- Records can be saved and retrieved.
- Invalid record relationships are rejected.

### Verification Steps
1. Add sample records to the database.
2. Verify that the records were saved.
3. Restart the application.
4. Verify that the information is still available.
5. Attempt to save a record with an invalid relationship.
6. Verify that the invalid record is rejected.

---

## Requirement 2 — Equipment Registration

**Story Points:** 5

### Description
Allow staff to register new equipment by entering its name, category, description, and unique asset ID.

### Inputs
- Equipment name
- Equipment category
- Equipment description
- Unique asset ID

### Expected Output
- New equipment is saved in the database.
- Equipment appears in the catalog.
- Duplicate asset IDs display an error message.

### Acceptance Criteria
- Staff can add equipment.
- Each equipment item has a unique asset ID.
- Equipment information is saved correctly.

### Verification Steps
1. Log in using a staff account.
2. Enter information for new equipment.
3. Save the equipment.
4. Verify that it appears in the catalog.
5. Attempt to register another item using the same asset ID.
6. Verify that the duplicate is rejected.

---

## Requirement 3 — Equipment Catalog

**Story Points:** 3

### Description
Display an equipment catalog where students can browse available equipment and view basic information about each item.

### Inputs
- Equipment information from the database
- User opening the catalog

### Expected Output
- Available equipment is displayed.
- Equipment names and details are shown.
- Unavailable equipment is not incorrectly displayed as available.

### Acceptance Criteria
- The catalog displays equipment information.
- Available equipment is shown correctly.
- The catalog loads without errors.

### Verification Steps
1. Add sample equipment to the database.
2. Open the Equipment Catalog.
3. Verify that the equipment appears.
4. Verify that the displayed information is correct.
5. Check that unavailable equipment is not shown as available.

---

## Requirement 4 — Navigation Menu

**Story Points:** 2

### Description
Display a navigation menu that allows users to access the main sections of CampusGear.

### Inputs
- User selecting a menu option

### Expected Output
- The selected page opens.
- Users can move between website sections.

### Acceptance Criteria
- The navigation menu is displayed.
- Links to implemented pages work correctly.
- Users can navigate without errors.

### Verification Steps
1. Open the CampusGear website.
2. Select the Equipment Catalog option.
3. Verify that the catalog opens.
4. Select another available menu option.
5. Verify that the correct page appears.
6. Verify that navigation works without errors.

---

## Requirement 5 — Student/Staff Login

**Story Points:** 8

### Description
Allow registered students and staff to securely log into and out of CampusGear.

### Inputs
- Email address
- Password

### Expected Output
- Valid student login opens the Student Interface.
- Valid staff login opens the Staff Interface.
- Invalid credentials display an error message.

### Acceptance Criteria
- Registered users can successfully log in.
- Incorrect passwords are rejected.
- Users can log out.
- Logged-out users cannot access protected pages.

### Verification Steps
1. Log in using a valid student account.
2. Verify that the Student Interface appears.
3. Log out.
4. Attempt to access a protected page.
5. Verify that login is required.
6. Repeat with a staff account.
7. Attempt login with an incorrect password.
8. Verify that access is denied.

---

## Requirement 6 — Student Privacy Protection

**Story Points:** 13

### Description
Protect students' private information by preventing unauthorized users from accessing student records or staff-only features.

### Inputs
- Logged-in user information
- User role (student or staff)
- Request to access protected information

### Expected Output
- Students can access their own private records.
- Students cannot access another student's information.
- Unauthorized requests are denied.

### Acceptance Criteria
- Students can only access their own private records.
- Students cannot perform staff-only actions.
- The backend checks user permissions before allowing access.

### Verification Steps
1. Log in using Student A's account.
2. Verify that Student A can access their own records.
3. Attempt to access Student B's information.
4. Verify that access is denied.
5. Attempt to access a staff-only function.
6. Verify that the request is rejected.
7. Log in as authorized staff.
8. Verify that permitted staff functions work correctly.

---

## Requirement 7 — Role-Specific Website Features

**Story Points:** 3

### Description
Display different website features depending on whether the user is a student or staff member.

### Inputs
- Logged-in user role

### Expected Output
- Students see borrowing and reservation options.
- Staff see equipment management options.
- Each user sees the correct interface.

### Acceptance Criteria
- Student accounts display student features.
- Staff accounts display staff features.
- The correct interface appears after login.

### Verification Steps
1. Log in using a student account.
2. Verify that borrowing and reservation options appear.
3. Log out.
4. Log in using a staff account.
5. Verify that equipment management options appear.
6. Confirm that student and staff interfaces display the appropriate options.
