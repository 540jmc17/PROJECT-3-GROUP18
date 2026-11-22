# CampusGear — Sprint 2 Plan and Requirements Artifacts

## Sprint Overview

**Sprint:** 2 of 4  
**Sprint Length:** 2 weeks  
**Total Product Backlog:** 189 story points  
**Sprint 2 Commitment:** 42 story points  

**Sprint Goal:** Build the core equipment reservation and checkout workflow. Students will be able to select reservation dates, create and cancel reservations, view their reservations and borrowing history, and see equipment due dates. Staff will be able to manage reservations, check out equipment, and record equipment returns.

## Sprint 2 Requirements

| Requirement ID | Requirement | Story Points | Priority |
|---|---|---:|---:|
| 8 | Allow students to select valid start and end dates when reserving equipment | 2 | 8 |
| 9 | Prevent students from reserving equipment that is already reserved or checked out | 8 | 9 |
| 10 | Students view only their own reservations; staff view and manage all reservations | 5 | 10 |
| 11 | Allow staff to check out equipment associated with an existing student reservation | 5 | 11 |
| 12 | Allow staff to check out available equipment directly to students without a prior reservation | 5 | 12 |
| 13 | Record equipment returns and update loan and equipment availability statuses | 5 | 13 |
| 15 | Allow students to cancel reservations before equipment is checked out | 5 | 15 |
| 16 | Display equipment due dates for each item checked out by a student | 2 | 16 |
| 25 | Display confirmation messages when students create or cancel reservations | 1 | 25 |
| 26 | Allow students to view their borrowing history | 3 | 26 |
| 29 | Display an on-screen confirmation after staff records an equipment return | 1 | 29 |
| | **Total** | **42** | |

## Sprint Goal

At the end of Sprint 2, students should be able to reserve available equipment for valid dates, view and cancel their reservations, and review their borrowing history and due dates. Staff should be able to check out equipment through either an existing reservation or a direct checkout, record equipment returns, and update equipment and loan statuses accordingly.

---

# Sprint 2 Requirements Artifacts

## Requirement 8 — Select Reservation Dates

**Story Points:** 2

**Description:**

The system shall allow students to select a start date and end date when creating an equipment reservation. The system must validate that the selected dates are valid before allowing the reservation to be submitted.

**Inputs:**
- Selected equipment
- Reservation start date
- Reservation end date
- Student account

**Expected Output:**
- A reservation request containing the selected equipment and dates.
- An error message if the selected dates are invalid.

**Acceptance Criteria:**
- Students can select a start date and end date when creating a reservation.
- The start date cannot be earlier than the current date.
- The end date must be later than the start date.
- The system does not submit a reservation with invalid dates.
- Valid dates are saved with the reservation.

**Verification Steps:**
1. Log in using a student account.
2. Navigate to the equipment catalog.
3. Select an available equipment item.
4. Enter a valid start date and end date.
5. Submit the reservation and verify that the dates are saved.
6. Attempt to select a start date earlier than the current date.
7. Verify that the system displays an error and does not submit the reservation.
8. Attempt to select an end date earlier than or equal to the start date.
9. Verify that the system rejects the invalid date range.

## Requirement 9 — Prevent Reservations for Unavailable Equipment

**Story Points:** 8

**Description:**

The system shall prevent students from reserving equipment that is already reserved or checked out during the requested reservation period. Before saving a reservation, the system must check the equipment's existing reservations and loan records to determine whether the equipment is available for the selected dates.

**Inputs:**
- Selected equipment
- Requested reservation start date
- Requested reservation end date
- Existing reservation records
- Existing loan records

**Expected Output:**
- A successfully saved reservation when the equipment is available.
- An error message when the equipment is already reserved or checked out during the requested period.

**Acceptance Criteria:**
- The system checks existing reservations before creating a new reservation.
- The system checks whether the equipment is checked out during the requested reservation period.
- Students cannot reserve equipment when an existing reservation overlaps the requested dates.
- Students cannot reserve equipment when an active checkout makes it unavailable during the requested dates.
- The system allows reservations when the equipment is available for the entire requested period.
- Unavailable equipment is not saved as a new reservation.

**Verification Steps:**
1. Log in using a student account.
2. Select equipment that has no existing reservations or active checkouts.
3. Enter valid reservation dates and submit the reservation.
4. Verify that the reservation is successfully saved.
5. Attempt to reserve the same equipment for dates that overlap an existing reservation.
6. Verify that the system displays an error and does not create another reservation.
7. Attempt to reserve equipment that is checked out during the requested period.
8. Verify that the system prevents the reservation.
9. Select dates that do not overlap existing reservations or active checkouts.
10. Verify that the system allows the reservation.

## Requirement 10 — View and Manage Reservations Based on User Role

**Story Points:** 5

**Description:**

The system shall allow students to view only their own reservations. Staff members shall be able to view and manage reservations belonging to all students.

**Inputs:**
- Logged-in user account
- User role (student or staff)
- Reservation records

**Expected Output:**
- Students see only reservations associated with their own accounts.
- Staff members can view reservations from all student accounts and access available reservation management actions.

**Acceptance Criteria:**
- Students can access a page displaying their reservations.
- Students cannot view reservations belonging to other students.
- Staff members can view reservations belonging to all students.
- Staff members can access reservation management actions.
- The system verifies the user's role before displaying reservation information.
- Unauthorized users cannot access another student's reservation information by changing a page URL or request.

**Verification Steps:**
1. Log in using a student account.
2. Navigate to the reservations page.
3. Verify that only reservations belonging to the logged-in student are displayed.
4. Attempt to access another student's reservation information.
5. Verify that access is denied.
6. Log out and log in using a staff account.
7. Navigate to the reservations management page.
8. Verify that reservations from multiple student accounts are displayed.
9. Verify that staff can access the available reservation management actions.

## Requirement 11 — Check Out Equipment from an Existing Reservation

**Story Points:** 5

**Description:**

The system shall allow staff members to check out equipment associated with an existing student reservation. When equipment is checked out, the system must verify the reservation, create a loan record, and update the reservation and equipment statuses.

**Inputs:**
- Student reservation
- Equipment associated with the reservation
- Student account
- Checkout date
- Expected return date
- Staff account performing the checkout

**Expected Output:**
- A new loan record associated with the student and equipment.
- The reservation status updated from Reserved to Checked Out.
- The equipment status updated to Checked Out.

**Acceptance Criteria:**
- Staff can locate and select an existing reservation.
- The system verifies that the reservation exists and is eligible for checkout.
- The system associates the checkout with the correct student and equipment.
- The system records the checkout date and expected return date.
- A loan record is created when checkout is completed.
- The reservation status changes from Reserved to Checked Out.
- The equipment status changes to Checked Out.
- The system prevents checkout of a reservation that has already been checked out or canceled.

**Verification Steps:**
1. Log in using a staff account.
2. Navigate to the reservation management page.
3. Select an existing student reservation.
4. Verify that the reservation is eligible for checkout.
5. Record the checkout and expected return dates.
6. Complete the checkout.
7. Verify that a loan record is created for the correct student and equipment.
8. Verify that the reservation status changes to Checked Out.
9. Verify that the equipment status changes to Checked Out.
10. Attempt to check out the same reservation again.
11. Verify that the system prevents duplicate checkout.

## Requirement 12 — Direct Equipment Checkout Without a Reservation

**Story Points:** 5

**Description:**

The system shall allow staff members to check out available equipment directly to a student without requiring an existing reservation. The system must record the student, equipment, checkout date, and expected return date.

**Inputs:**
- Student account
- Selected available equipment
- Checkout date
- Expected return date
- Staff account performing the checkout

**Expected Output:**
- A new loan record associated with the selected student and equipment.
- The equipment status updated to Checked Out.
- The checkout and expected return dates saved.

**Acceptance Criteria:**
- Staff members can select a student account for direct checkout.
- Staff members can select equipment that is currently available.
- The system records the student and equipment associated with the checkout.
- The system records the checkout date and expected return date.
- A loan record is created without requiring a reservation.
- The equipment status changes to Checked Out.
- The system prevents direct checkout of equipment that is already reserved or checked out.
- The expected return date must be later than the checkout date.

**Verification Steps:**
1. Log in using a staff account.
2. Navigate to the direct checkout page.
3. Select a student account.
4. Select equipment that is currently available.
5. Enter a checkout date and expected return date.
6. Submit the checkout.
7. Verify that a loan record is created for the selected student and equipment.
8. Verify that the checkout and expected return dates are saved.
9. Verify that the equipment status changes to Checked Out.
10. Attempt to check out equipment that is already unavailable.
11. Verify that the system prevents the checkout.

## Requirement 13 — Record Equipment Returns

**Story Points:** 5

**Description:**

The system shall allow staff members to record the return of checked-out equipment. When equipment is returned, the system must update the associated loan record and equipment status. Equipment returned in usable condition shall become available for future reservations. Equipment that is damaged or requires repair shall remain unavailable.

**Inputs:**
- Existing loan record
- Equipment associated with the loan
- Return date
- Equipment condition upon return
- Staff account recording the return

**Expected Output:**
- The loan record updated with the return date.
- The loan status updated to Returned.
- The equipment status updated to Available if usable, or Unavailable if it requires repair.

**Acceptance Criteria:**
- Staff members can locate an active loan record.
- The system allows staff to record the equipment return date.
- The loan status changes to Returned after the return is recorded.
- The equipment status changes to Available when the returned equipment is usable.
- The equipment remains Unavailable when it is damaged or requires repair.
- The system prevents an already returned loan from being returned a second time.
- The return information is saved and associated with the correct loan and equipment.

**Verification Steps:**
1. Log in using a staff account.
2. Navigate to the active loans or checkout management page.
3. Select an equipment loan that has not been returned.
4. Record the return date.
5. Indicate that the equipment is in usable condition.
6. Submit the return.
7. Verify that the loan status changes to Returned.
8. Verify that the return date is saved.
9. Verify that the equipment status changes to Available.
10. Repeat the process with another active loan, but indicate that the equipment is damaged or requires repair.
11. Verify that the loan status changes to Returned and the equipment remains Unavailable.
12. Attempt to record a return for an already returned loan.
13. Verify that the system prevents a duplicate return.

## Requirement 15 — Cancel Reservations Before Checkout

**Story Points:** 5

**Description:**

The system shall allow students to cancel their own reservations before the equipment has been checked out. When a reservation is canceled, the system must update its status and make the equipment available for other reservations when no other restriction applies.

**Inputs:**
- Logged-in student account
- Selected reservation
- Current reservation status

**Expected Output:**
- The reservation status updated to Canceled.
- The equipment made available for future reservations when no other reservation, checkout, or maintenance restriction applies.

**Acceptance Criteria:**
- Students can view their own reservations.
- Students can cancel reservations that have not been checked out.
- The system updates the reservation status to Canceled.
- Students cannot cancel reservations belonging to other students.
- Students cannot cancel reservations after the equipment has been checked out.
- The system updates equipment availability when cancellation makes the equipment available.
- Canceled reservations remain recorded in the system.

**Verification Steps:**
1. Log in using a student account.
2. Navigate to the student's reservations page.
3. Select a reservation that has not been checked out.
4. Cancel the reservation.
5. Verify that the reservation status changes to Canceled.
6. Verify that the equipment becomes available when no other restriction applies.
7. Attempt to cancel a reservation belonging to another student.
8. Verify that the system denies the action.
9. Attempt to cancel a reservation that has already been checked out.
10. Verify that the system prevents the cancellation.

## Requirement 16 — Display Equipment Due Dates

**Story Points:** 2

**Description:**

The system shall display the expected return date for each item currently checked out by a student. Students must be able to view the due dates associated with their active loans.

**Inputs:**
- Logged-in student account
- Active loan records
- Expected return dates
- Associated equipment information

**Expected Output:**
- A list of equipment currently checked out by the student.
- The expected return date displayed for each checked-out item.

**Acceptance Criteria:**
- Students can view their currently checked-out equipment.
- Each active loan displays its associated expected return date.
- The displayed due date corresponds to the correct equipment item.
- Students cannot view another student's active loan information.
- Returned equipment is no longer displayed as an active checkout.

**Verification Steps:**
1. Log in using a student account with at least one active loan.
2. Navigate to the student's checked-out equipment page.
3. Verify that each checked-out item is displayed.
4. Verify that the expected return date is displayed for each item.
5. Compare the displayed due dates with the corresponding loan records.
6. Verify that returned equipment does not appear in the active checkout list.
7. Log in using another student account and verify that the first student's loan information is not displayed.

## Requirement 25 — Reservation Confirmation Messages

**Story Points:** 1

**Description:**

The system shall display a confirmation message when a student successfully creates or cancels an equipment reservation. The message must indicate which action was completed.

**Inputs:**
- Student account
- Reservation information
- Reservation creation or cancellation action
- Result of the requested action

**Expected Output:**
- A confirmation message after a reservation is successfully created.
- A confirmation message after a reservation is successfully canceled.
- An error message if the requested action is unsuccessful.

**Acceptance Criteria:**
- A confirmation message is displayed after a successful reservation.
- A confirmation message is displayed after a successful cancellation.
- The message clearly identifies the completed action.
- The system does not display a success message when the action fails.
- The reservation or cancellation is saved before the success message is displayed.

**Verification Steps:**
1. Log in using a student account.
2. Select available equipment and submit a valid reservation.
3. Verify that a reservation confirmation message is displayed.
4. Verify that the reservation was successfully saved.
5. Navigate to the student's reservations page.
6. Cancel a reservation that has not been checked out.
7. Verify that a cancellation confirmation message is displayed.
8. Attempt an invalid reservation.
9. Verify that the system displays an error rather than a success message.

## Requirement 26 — View Borrowing History

**Story Points:** 3

**Description:**

The system shall allow students to view their borrowing history, including equipment previously borrowed, checkout dates, and return dates. Students must only be able to access their own borrowing history.

**Inputs:**
- Logged-in student account
- Historical loan records
- Associated equipment information
- Checkout dates
- Return dates

**Expected Output:**
- A list of the student's previous equipment loans.
- Each loan displays the equipment name, checkout date, and return date when available.

**Acceptance Criteria:**
- Students can navigate to a borrowing history page.
- The system displays previously borrowed equipment associated with the logged-in student.
- Each historical loan displays the equipment name.
- Each historical loan displays its checkout date.
- Each historical loan displays its return date when the equipment has been returned.
- Students cannot view borrowing history belonging to other students.
- Active loans are not incorrectly displayed as completed returns.

**Verification Steps:**
1. Log in using a student account with previous loan records.
2. Navigate to the borrowing history page.
3. Verify that previously borrowed equipment is displayed.
4. Verify that each record displays the correct equipment name and checkout date.
5. Verify that returned equipment displays its return date.
6. Verify that active loans do not display an incorrect return date.
7. Log in using another student account.
8. Verify that the first student's borrowing history is not accessible.

## Requirement 29 — Equipment Return Confirmation

**Story Points:** 1

**Description:**

The system shall display an on-screen confirmation after a staff member successfully records an equipment return. The confirmation must include the equipment name and return date.

**Inputs:**
- Staff account
- Equipment being returned
- Associated loan record
- Return date
- Result of the return operation

**Expected Output:**
- A confirmation message displaying the equipment name and return date after a successful return.
- An error message if the return operation is unsuccessful.

**Acceptance Criteria:**
- A confirmation message is displayed after a return is successfully recorded.
- The message includes the equipment name.
- The message includes the recorded return date.
- The confirmation is displayed only after the return information has been saved.
- The system does not display a successful return confirmation when the operation fails.

**Verification Steps:**
1. Log in using a staff account.
2. Navigate to the active loans or checkout management page.
3. Select an equipment loan that has not been returned.
4. Record the equipment return.
5. Verify that the return operation completes successfully.
6. Verify that an on-screen confirmation message appears.
7. Verify that the message includes the correct equipment name and return date.
8. Attempt to record an invalid or duplicate return.
9. Verify that the system displays an error rather than a successful return confirmation.
