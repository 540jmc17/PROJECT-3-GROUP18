# CampusGear — Sprint 3 Plan and Requirements Artifacts

## Sprint Overview

**Sprint:** 3 of 4  
**Sprint Length:** 2 weeks  
**Total Product Backlog:** 189 story points  
**Sprint 3 Commitment:** 63 story points  

Sprint 3 focuses on preventing simultaneous double bookings, managing equipment that is under repair, supporting equipment and damage records, improving catalog search, displaying overdue notifications and equipment dashboard totals, displaying equipment details and history, and allowing staff to extend loan due dates when no reservation conflict exists.

## Sprint 3 Requirements

| Requirement ID | Description | Story Points |
|---|---|---:|
| 14 | Prevent simultaneous double bookings. | 8 |
| 17 | Allow staff to mark equipment as unavailable while it is being repaired. | 3 |
| 18 | Block reservations during repairs or maintenance. | 5 |
| 19 | Display option for staff to create and manage repair tickets. | 5 |
| 20 | Staff can edit existing equipment information, including its name, category, description, and condition. Changes must be saved and reflected on the website. | 3 |
| 21 | Allow users to search for equipment by name and filter the catalog by equipment category or current availability. | 5 |
| 22 | Report damaged equipment for students and allow staff to view and manage damage reports. | 8 |
| 23 | Notify staff for all overdue equipment and notify students when their borrowed equipment is overdue. | 5 |
| 24 | Display equipment dashboard totals for equipment items, available items, reserved items, checked-out items, and overdue loans. | 5 |
| 27 | Display each equipment item's details and history. | 3 |
| 28 | Allow staff to extend the return date of equipment currently checked out if the extension does not conflict with another student's reservation. | 13 |
| **Total** |  | **63** |

## Sprint Goal

By the end of Sprint 3, CampusGear will provide more reliable equipment reservation and loan management. The system will prevent simultaneous double bookings, prevent reservations for equipment marked as under repair, and provide staff with tools to manage equipment information, repair tickets, and damage reports. Users will be able to search and filter the equipment catalog. Staff and students will receive overdue notifications, staff will be able to view equipment totals on a dashboard, users will be able to view equipment details and history, and staff will be able to extend an active loan's return date only when the extension does not conflict with another student's reservation.

# Sprint 3 Requirements Artifacts

## Requirement 14 — Prevent simultaneous double bookings

**Story Points:** 8

### Description

The system must prevent two students from successfully reserving the same equipment for overlapping dates when their reservation requests are submitted at nearly the same time. The system must verify equipment availability when a reservation is submitted and make the reservation operation safe against concurrent requests. A check performed only in the browser is not sufficient; the final availability check and reservation creation must be handled safely by the server and data layer.

### Inputs

- Student account submitting the reservation.
- Equipment item selected by the student.
- Requested reservation start date.
- Requested reservation end date.
- Existing reservation and loan records for the selected equipment.

### Expected Output

- If the equipment is available for the requested dates, one reservation is saved successfully.
- If another request has already reserved the equipment for overlapping dates, the later conflicting request is rejected.
- The student receives a clear message explaining that the equipment is no longer available for the selected dates.
- The database does not contain two conflicting successful reservations created by simultaneous requests.

### Acceptance Criteria

1. The server checks the selected equipment's current reservation and loan records when the student submits a reservation.
2. The availability check and creation of the reservation are performed as one concurrency-safe operation, such as through an appropriate database transaction or equivalent protection.
3. Two requests for the same equipment with overlapping dates cannot both complete successfully.
4. A rejected request does not create a reservation record.
5. A student receives a useful success or conflict message after submitting the request.
6. Existing reservation rules and date validation continue to apply.

### Verification Steps

1. Sign in as two different student accounts.
2. Submit reservation requests for the same equipment and overlapping dates from the two accounts at nearly the same time.
3. Confirm that no more than one request succeeds.
4. Confirm that the unsuccessful request displays an availability message.
5. Inspect the database or reservation list and confirm that only one conflicting reservation was saved.
6. Repeat the test with non-overlapping dates and confirm that both valid reservations can be saved when the equipment's schedule permits them.

## Requirement 17 — Allow staff to mark equipment as unavailable while it is being repaired

**Story Points:** 3

### Description

The system must allow an authorized staff member to mark an equipment item as unavailable while it is being repaired. The equipment's updated status must be saved and reflected wherever the equipment's availability is displayed. This requirement records that the equipment is unavailable; reservation blocking is addressed by Requirement 18.

### Inputs

- Staff account.
- Equipment item selected by staff.
- Updated availability or repair status indicating that the equipment is unavailable while being repaired.

### Expected Output

- The equipment's unavailable/under-repair status is saved.
- The updated status is displayed on the equipment's staff view and relevant catalog views.
- The equipment is no longer presented as generally available while the repair status is active.

### Acceptance Criteria

1. Only an authorized staff member can change the equipment's repair availability status.
2. Staff can select an equipment item and mark it as unavailable while it is being repaired.
3. The change is saved to persistent storage.
4. The updated status remains in effect after the page is refreshed or the user signs in again.
5. The equipment's displayed availability reflects the saved status.
6. A staff member can update the status when the equipment is no longer under repair and is usable again.

### Verification Steps

1. Sign in using a staff account.
2. Open the equipment management area and select an equipment item.
3. Mark the item as unavailable/under repair and save the change.
4. Refresh the page and confirm that the updated status remains visible.
5. View the catalog and confirm that the item is not displayed as available.
6. Update the item after the repair is complete and confirm that its status changes accordingly.
7. Sign in as a student and confirm that the student cannot change the equipment's repair status.

## Requirement 18 — Block reservations during repairs or maintenance

**Story Points:** 5

### Description

The system must prevent students from reserving equipment while it is marked as unavailable because it is being repaired or undergoing maintenance. The reservation process must check the equipment's saved repair/maintenance availability status on the server before creating a reservation. Hiding or disabling a reservation button alone does not satisfy this requirement.

### Inputs

- Student account submitting a reservation.
- Equipment item selected for reservation.
- Requested reservation start and end dates.
- Equipment's current saved availability and repair/maintenance status.

### Expected Output

- A reservation for equipment marked as under repair or maintenance is rejected.
- No reservation record is created for the rejected request.
- The student receives a message explaining that the equipment cannot be reserved while it is under repair or maintenance.
- Equipment that is returned to an eligible available status can be reserved again, subject to the other reservation rules.

### Acceptance Criteria

1. The reservation service checks the equipment's current repair/maintenance status before saving a reservation.
2. Students cannot reserve equipment while its status indicates that it is unavailable because of repair or maintenance.
3. The restriction is enforced by the server, including when a reservation request is submitted without using the normal page controls.
4. A rejected request does not create a reservation record.
5. The student receives a clear explanation for the rejection.
6. Equipment can become reservable again after staff update its status, provided no other reservation or loan conflict exists.

### Verification Steps

1. Sign in as staff and mark an equipment item as unavailable while under repair.
2. Sign in as a student and open the equipment catalog.
3. Attempt to reserve the equipment for otherwise valid dates.
4. Confirm that the system rejects the reservation and explains why.
5. Confirm that no reservation was added to the database or reservation list.
6. Sign in as staff and mark the equipment as available after the repair is complete.
7. Attempt a valid reservation again and confirm that the maintenance restriction no longer blocks it.

## Requirement 19 — Display option for staff to create and manage repair tickets

**Story Points:** 5

### Description

The system must provide staff with an option to create and manage repair tickets for equipment that needs repair. A repair ticket must be associated with the relevant equipment item and store the information staff need to track the repair. Staff must be able to view existing tickets and update their information or repair status.

### Inputs

- Authorized staff account.
- Equipment item associated with the repair.
- Repair description or issue details.
- Repair ticket status.
- Any ticket information staff update while managing the ticket.

### Expected Output

- Staff can create a repair ticket associated with an equipment item.
- The new ticket is saved and appears in the staff repair-ticket view.
- Staff can open an existing ticket and update its information or status.
- The saved ticket information remains available after the page is refreshed.

### Acceptance Criteria

1. A repair-ticket option is available to authorized staff.
2. Staff can select the equipment item associated with a repair ticket.
3. Staff can enter the repair description and create the ticket.
4. The system saves the ticket and associates it with the selected equipment item.
5. Staff can view existing repair tickets.
6. Staff can update the information or status of an existing repair ticket.
7. Changes to a repair ticket are saved and remain visible after refreshing the page.
8. Students cannot create or manage staff repair tickets.

### Verification Steps

1. Sign in as staff.
2. Open the repair-ticket area and create a ticket for an equipment item that needs repair.
3. Enter a repair description and save the ticket.
4. Confirm that the ticket appears in the staff ticket list and is associated with the correct equipment item.
5. Open the ticket, update its status or information, and save the change.
6. Refresh the page and confirm that the updated information remains visible.
7. Sign in as a student and confirm that staff repair-ticket management controls are not available.

## Requirement 20 — Staff can edit existing equipment information

**Story Points:** 3

### Description

The system must allow staff to edit an existing equipment item's name, category, description, and condition. After staff save their changes, the updated information must be stored and reflected on the website, including the equipment catalog and equipment details view.

### Inputs

- Authorized staff account.
- Existing equipment item selected for editing.
- Updated equipment name.
- Updated equipment category.
- Updated equipment description.
- Updated equipment condition.

### Expected Output

- The system saves the updated equipment information.
- The staff view, catalog, and equipment details view display the current saved information.
- The changes remain after the page is refreshed.

### Acceptance Criteria

1. Only authorized staff can edit equipment information.
2. Staff can open an existing equipment item for editing.
3. Staff can update the item's name, category, description, and condition.
4. The system validates required information before saving.
5. The updated information is saved to persistent storage.
6. Updated information is reflected wherever that equipment item is displayed.
7. Students cannot access the equipment editing controls.

### Verification Steps

1. Sign in as staff and open the equipment management area.
2. Select an existing equipment item and edit its name, category, description, and condition.
3. Save the changes.
4. Refresh the page and reopen the equipment item.
5. Confirm that all updated fields contain the saved values.
6. Open the student-facing catalog and confirm that the updated information is displayed.
7. Sign in as a student and confirm that the student cannot edit the equipment information.

## Requirement 21 — Allow users to search for equipment by name and filter the catalog

**Story Points:** 5

### Description

The system must allow users to search the equipment catalog by equipment name and filter the displayed equipment by category or current availability. Search and filter results must reflect the equipment records currently stored in the system.

### Inputs

- Search text entered by the user.
- Optional equipment category filter.
- Optional current-availability filter.
- Equipment catalog records.

### Expected Output

- The catalog displays equipment whose names match the search text.
- The catalog can be filtered by selected equipment category.
- The catalog can be filtered by current availability.
- When more than one search or filter option is selected, the displayed results satisfy the selected criteria.
- The user can clear the search and filters to return to the unfiltered catalog.

### Acceptance Criteria

1. Users can enter a name or partial name to search the catalog.
2. Search matching is not dependent on capitalization.
3. Users can filter the catalog by equipment category.
4. Users can filter the catalog by current availability.
5. Search and filters can be applied together.
6. Results reflect the current saved equipment status and availability.
7. The catalog displays an understandable message when no equipment matches the selected criteria.
8. Users can clear the search and filters.

### Verification Steps

1. Open the equipment catalog as a student or staff user.
2. Search for an equipment item using its full name and confirm that the matching item appears.
3. Search using part of an equipment name and confirm that matching results appear.
4. Change the capitalization of the search text and confirm that the results remain correct.
5. Select a category filter and confirm that only equipment in that category appears.
6. Select an availability filter and confirm that the results match the selected availability.
7. Apply a search and a filter together and confirm that both criteria are applied.
8. Enter a search or filter combination with no matches and confirm that an appropriate empty-results message appears.
9. Clear the search and filters and confirm that the catalog returns to its normal list.

## Requirement 22 — Report damaged equipment for students and allow staff to view and manage damage reports

**Story Points:** 8

### Description

The system must allow students to submit a damage report for an equipment item. Staff must be able to view submitted damage reports and manage them. A damage report must identify the equipment item and describe the damage so staff can determine what action is needed. Damage reports are separate records from repair tickets; staff may use a damage report when deciding whether to create a repair ticket.

### Inputs

- Student account submitting the report.
- Equipment item being reported.
- Description of the damage or issue.
- Submission date/time recorded by the system.
- Staff updates made while managing the report.

### Expected Output

- The damage report is saved and associated with the selected equipment item and submitting student.
- The student receives confirmation that the report was submitted.
- Authorized staff can view submitted damage reports.
- Staff can update or manage a report, and the saved changes remain available.

### Acceptance Criteria

1. A student can access an option to report damaged equipment.
2. The student can select the relevant equipment item and provide a description of the damage.
3. The system validates that the required report information is provided.
4. The report is saved and associated with the correct equipment item and submitting student.
5. The student receives a confirmation after submitting the report.
6. Authorized staff can view submitted damage reports.
7. Staff can manage a report, including updating its handling status or recorded staff information.
8. A student cannot view or manage another student's private report information.
9. A student cannot access staff-only damage-report management controls.

### Verification Steps

1. Sign in as a student and open the damage-report option.
2. Select an equipment item, enter a damage description, and submit the report.
3. Confirm that the student sees a submission confirmation.
4. Sign in as staff and open the damage-report management view.
5. Confirm that the new report appears with the correct equipment item and description.
6. Update the report's handling status or staff information and save the change.
7. Refresh the page and confirm that the update remains saved.
8. Sign in as a different student and verify that the first student's private report information is not exposed.

## Requirement 23 — Notify staff and students about overdue equipment

**Story Points:** 5

### Description

The system must notify staff about all equipment loans that are overdue and notify each student when their own borrowed equipment is overdue. A loan is overdue when its expected return date has passed and the equipment has not been recorded as returned. Notifications must be based on saved loan information and must not expose one student's private loan information to another student.

### Inputs

- Active loan records.
- Student associated with each loan.
- Equipment associated with each loan.
- Expected return date.
- Current date used to determine whether the loan is overdue.
- Loan return status.

### Expected Output

- Staff can see overdue notifications or an overdue list covering all overdue loans.
- A student can see an overdue notification for their own overdue loan.
- Loans that have been returned are not shown as currently overdue.
- Notifications identify the relevant equipment and expected return date without exposing another student's private loan information.

### Acceptance Criteria

1. The system identifies a loan as overdue when its expected return date has passed and its status is not returned.
2. Staff can see all loans that are currently overdue.
3. Each student is notified about their own overdue loan or loans.
4. Students cannot see overdue loan details belonging to other students.
5. A loan recorded as returned is no longer treated as currently overdue.
6. Overdue information is based on saved loan records and the current date.
7. Repeated page loads do not create an uncontrolled number of duplicate notifications for the same overdue event.

### Verification Steps

1. Prepare an active loan with an expected return date in the past.
2. Sign in as the student associated with that loan and confirm that an overdue notification is displayed.
3. Sign in as staff and confirm that the overdue loan appears in the staff overdue view or notification area.
4. Sign in as a different student and confirm that the first student's overdue loan details are not visible.
5. Record the loan as returned.
6. Refresh the student and staff views and confirm that the loan is no longer listed as currently overdue.
7. Reload the pages more than once and confirm that duplicate notifications are not repeatedly created for the same overdue event.

## Requirement 24 — Display equipment dashboard totals

**Story Points:** 5

### Description

The system must display a staff equipment dashboard showing totals for all registered equipment items, available items, reserved items, checked-out items, and overdue loans. The dashboard totals must be calculated from the current saved equipment, reservation, and loan records.

### Inputs

- Equipment records.
- Current equipment availability or repair status.
- Active reservation records.
- Active loan records.
- Loan expected return dates and return statuses.

### Expected Output

The staff dashboard displays the following totals:

- Total equipment items.
- Available equipment items.
- Reserved equipment items.
- Checked-out equipment items.
- Overdue loans.

The totals update when relevant equipment, reservation, or loan records change.

### Acceptance Criteria

1. The dashboard is available to authorized staff.
2. The dashboard displays the total number of registered equipment items.
3. The dashboard displays the number of equipment items currently available.
4. The dashboard displays the number of equipment items currently reserved.
5. The dashboard displays the number of equipment items currently checked out.
6. The dashboard displays the number of currently overdue loans.
7. Returned loans are not included in the overdue-loan total.
8. Equipment marked unavailable for repair or maintenance is not counted as available.
9. Dashboard totals are calculated from saved records and reflect relevant updates after the dashboard is refreshed or reloaded.
10. Students cannot access the staff dashboard.

### Verification Steps

1. Sign in as staff and open the equipment dashboard.
2. Compare the total equipment count with the equipment records.
3. Compare the available, reserved, and checked-out totals with the current equipment, reservation, and loan records.
4. Prepare or identify an overdue active loan and confirm that the overdue-loan total includes it.
5. Return the overdue loan and refresh the dashboard; confirm that the overdue-loan total decreases accordingly.
6. Mark an equipment item as under repair and refresh the dashboard; confirm that it is not counted as available.
7. Sign in as a student and confirm that the staff dashboard is not accessible.

## Requirement 27 — Display each equipment item's details and history

**Story Points:** 3

### Description

The system must provide a details view for each equipment item and display that item's relevant history. The details view must identify the selected equipment and show its current information. The history must show available past equipment activity, such as reservation and loan events, in a clear order. The view must respect the application's privacy and role restrictions and must not reveal another student's private information. Equipment maintenance history is handled separately by Requirement 33.

### Inputs

- Equipment item selected by the user.
- Saved equipment information, such as asset ID, name, category, description, condition, and current status.
- Reservation and loan history associated with the equipment item.
- User's role and access permissions.

### Expected Output

- The selected equipment item's details are displayed.
- Relevant historical reservation and loan activity for the equipment item is displayed.
- History entries are presented in a clear, consistent order, such as newest first.
- Personal information about other students is hidden from users who are not authorized to see it.

### Acceptance Criteria

1. A user can open the details view for an equipment item from the catalog or another appropriate equipment list.
2. The details view displays the selected item's identifying information and current saved status.
3. The details view displays the available reservation and loan history associated with that equipment item.
4. History entries include useful activity information, such as the event type and relevant dates or status.
5. The history is displayed in a consistent order.
6. The system enforces the user's role and privacy permissions when displaying history.
7. The details and history shown are associated with the selected equipment item, not another item.

### Verification Steps

1. Open the equipment catalog and select an equipment item.
2. Open its details view and confirm that its identifying information and current status are displayed.
3. Confirm that the item's reservation and loan history appears when historical records exist.
4. Confirm that history entries show the correct equipment activity and relevant dates or statuses.
5. Open a different equipment item and verify that its details and history are not mixed with the first item's records.
6. Sign in with different user roles and verify that the history view does not reveal private information to unauthorized users.
7. Confirm that an item with no historical reservation or loan activity displays an appropriate empty-history message.

## Requirement 28 — Allow staff to extend the return date of checked-out equipment when no reservation conflict exists

**Story Points:** 13

### Description

The system must allow authorized staff to extend the expected return date of equipment that is currently checked out to a student. Before saving the extension, the system must check whether the extended loan period would conflict with another student's reservation for the same equipment. If a conflict exists, the extension must be rejected and the original return date must remain unchanged. Students cannot extend their own due dates through this requirement; the extension is performed by staff.

### Inputs

- Authorized staff account.
- Active loan selected for extension.
- Equipment item associated with the active loan.
- Student associated with the active loan.
- Current expected return date.
- Proposed new expected return date.
- Existing reservations for the same equipment.

### Expected Output

- If the proposed extension does not conflict with another student's reservation, the system saves the new expected return date.
- The updated due date is displayed in the relevant staff loan view and student loan view.
- If the proposed extension conflicts with another student's reservation, the system rejects the change, displays an explanation, and leaves the original due date unchanged.
- Returned loans cannot be extended.

### Acceptance Criteria

1. Only authorized staff can access the loan-extension function.
2. Staff can select equipment that is currently checked out and view its current expected return date.
3. Staff can enter a proposed later return date.
4. The system verifies that the selected loan is still active and has not been returned.
5. The system checks reservations for the same equipment before saving the extension.
6. The extension is rejected when the proposed extended loan period overlaps another student's reservation.
7. When a conflict is found, the system displays a clear message and does not change the original due date.
8. When no conflict is found, the system saves the new expected return date.
9. The new due date is reflected in the relevant staff and student views after saving.
10. Students cannot use this staff function to extend their own loan due dates.

### Verification Steps

1. Sign in as staff and open the active loans or checkout-management view.
2. Select a loan that is currently checked out and verify that its current due date is displayed.
3. Identify or create another student's reservation for the same equipment that overlaps the proposed extension period.
4. Attempt to extend the active loan past the conflicting reservation date.
5. Confirm that the extension is rejected, a conflict message is displayed, and the original due date remains unchanged.
6. Select an active loan whose proposed extension period does not conflict with another reservation for that equipment.
7. Save the extension and confirm that the new due date is displayed in the staff view.
8. Sign in as the student associated with the loan and confirm that the updated due date is displayed.
9. Attempt to extend a returned loan and confirm that the system rejects the request.
10. Sign in as a student and confirm that the student cannot access the staff loan-extension controls.
