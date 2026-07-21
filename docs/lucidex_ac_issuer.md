# LUCIDEX — Acceptance Criteria: ISSUER PORTAL (US 1.0–1.9)

## 1.0 — Issuer Registration

User Story:

As an upcoming Issuer institution,
I want to submit my registration through a dedicated form,
So that I can apply without relying on email-based submission.

AC:

Scenario: Successful form submission
Given an upcoming Issuer accesses the Issuer Registration page
When they fill in all required fields:
| Field |
| Institution name |
| Tax code |
| Registered address |
| Legal representative's name |
| Contact Gmail |
| Contact phone |
| Registrant's name |
And they submit the form
Then the application is created with status "pending review"
And a confirmation message "Your registration application has been submitted successfully and is pending review." is shown to the registrant

Scenario: Submission with missing required fields
Given the Issuer is filling out the Registration form
When one or more required fields are left empty
Then the form cannot be submitted
And the missing fields are highlighted

Scenario: Invalid field format
Given the Issuer enters data in an invalid format (e.g. malformed tax code, invalid
Gmail address, invalid phone number)
When they attempt to submit the form
Then a validation error is shown for each invalid field
And the form is not submitted

Scenario: Application enters Admin review queue
Given a registration form has been successfully submitted
When the application is created
Then it appears in the Admin's approval queue (Flow 4.1–4.3) with status "pending review"

## 1.1 — Onboarding & Account Provisioning

User Story:

As an approved Issuer institution,
I want to receive a one-time invite link via my registered contact email,
so that I can set up my own admin account without depending on a specific email domain.

AC:

Scenario: Invite link sent after admin approval
Given an Issuer application has been approved by the Admin
When the approval is confirmed
Then an invitation email with the subject "Issuer Account Setup Invitation" is sent
to the registered contact email
And the link is valid for one single use only

Scenario: Issuer sets up account with valid password
Given the Issuer clicks a valid, unused invite link
When they submit a new username, a password, and a matching confirm password
And the password meets the minimum security requirements
| Requirement |
| At least 8 characters |
| At least 1 uppercase letter |
| At least 1 lowercase letter |
| At least 1 number |
| At least 1 special character |
Then the account is created
And the user is redirected to mandatory 2FA setup (Flow 1.2)

Scenario: Password and confirm password do not match
Given the Issuer clicks a valid, unused invite link
When they enter a password and a confirm password that do not match
Then an error message "Password and Confirm Password do not match." is displayed
And the account is not created

Scenario: Password does not meet security requirements
Given the Issuer clicks a valid, unused invite link
When they enter a password that fails one or more security requirements
Then an error message "Password must contain at least 8 characters, 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character." is displayed
And the account is not created

Scenario: Reused invite link
Given an invite link was already used
When the Issuer attempts to access it
Then an error message "This invitation link has already been used." is displayed
And no account is created

## 1.2 — Login

User Story: As an Issuer Admin, I want to log in using my username, password, and 2FA, so that only verified staff can access sensitive credential data.

AC:

Scenario: Successful login
Given a registered Issuer Admin with valid credentials
When they enter correct username and password
And they complete the 2FA challenge successfully
Then they are granted access to the Issuer Portal at Home Page

Scenario: Login fails without 2FA
Given valid username and password are entered
When 2FA verification is not completed
Then access to the Portal is denied

Scenario: Invalid credentials
Given incorrect username or password is entered
When the Issuer attempts to log in
Then an error message "Invalid login credentials." is shown
And no session is created

## 1.3 — 2FA Setup

User Story: As an Issuer Admin, I want to set up two-factor authentication via authenticator app or SMS, so that my account is protected against unauthorized access.

AC:

Scenario: Default 2FA setup via email OTP
Given the Issuer Admin has completed account registration
When the 2FA setup popup appears
Then an OTP is automatically sent to the registered contact email
And the Issuer Admin can enter the OTP to activate 2FA

Scenario: Successful verification via email OTP
Given an OTP has been sent to the registered contact email
When the Issuer Admin enters the correct OTP
Then 2FA is activated for the account with email as the default method

Scenario: Switch to SMS method
Given the 2FA setup popup is displayed with email as the default method
When the Issuer Admin selects "Switch to SMS"
Then an OTP is sent to the phone number registered at sign-up
And the Issuer Admin can enter the OTP to activate 2FA via SMS

Scenario: Successful verification via SMS OTP
Given an OTP has been sent to the registered phone number
When the Issuer Admin enters the correct OTP
Then 2FA is activated for the account with SMS as the method

Scenario: Switch back from SMS to email
Given the Issuer Admin is on the SMS OTP verification step
When they select "Switch to email"
Then an OTP is sent to the registered contact email
And the Issuer Admin can enter the OTP to activate 2FA via email

Scenario: Incorrect OTP entered
Given an OTP has been sent (via email or SMS)
When the Issuer Admin enters an incorrect code
Then an error message "Invalid OTP. Please try again." is displayed
And 2FA is not activated

Scenario: OTP expired
Given an OTP has been sent (via email or SMS)
When the Issuer Admin attempts to verify after the OTP expiry window
Then an error message"OTP has expired. Please request a new code." is displayed
And the Issuer Admin can request a new OTP

Scenario: 2FA enforced on every login
Given 2FA has been activated
When the Issuer Admin logs in at any time
Then 2FA verification is required and cannot be skipped
And access to the Portal is granted only after successful 2FA verification

## 1.4 — Forgot Password

User Story:

As an Issuer Admin who forgot my password,

I want to reset it via a time-limited email link,

So that I can regain access securely.

AC:

Scenario: Valid reset request within time limit
Given the Issuer Admin requests a password reset
When they click the reset link within 30 minutes
Then they can set a new password
And the new password must comply with the password rules given at US 1.1
And they must re-confirm 2FA to complete login
And a confirmation message "Your password has been reset successfully." is displayed

Scenario: Expired reset link
Given a password reset link was requested
When more than 30 minutes have passed
Then the link is invalid
And an error message "This password reset link has expired. Please request a new reset link." is displayed
And the Issuer Admin must request a new link

Scenario: Reset requested for unregistered email
Given an email not associated with any Issuer account is entered
When the reset request is submitted
Then no reset link is sent (no account enumeration disclosed)
And a message "If an account exists for this email address, a password reset link will be sent." is displayed

## 1.5 — Upload Graduate CSV

User Story:

As an Issuer Admin,

I want to upload a graduate CSV file with a defined structure,

So that digital representations are automatically created for valid records.

AC:

Scenario: Download CSV template
Given the Issuer Admin is on the Upload Graduate CSV page
When they click "Download CSV Template"
Then a CSV template is downloaded containing the following columns:
| Column |
| Student ID |
| Full name |
| DOB |
| Major |
| Graduation year |
| Graduation classification |
| University email |
| National ID (hashed) |
| Phone number (optional) |

Scenario: Reject non-CSV file
Given the Issuer Admin selects a file to upload
When the file is not in .csv format
Then the file is rejected
And a popup message informs the user that only .csv files are accepted. The message is "Only files with .csv format are accepted. Please select the correct file format."

Scenario: Reject file exceeding size limit
Given the Issuer Admin selects a .csv file
When the file size exceeds 20MB
Then the file is rejected
And a popup message informs the user of the 20MB size limit. The message is "Only files with under 20MB size are accepted. Please select files with suitable size."

Scenario: Reject file with invalid structure
Given a .csv file within the size limit is uploaded
When the file's column structure does not match the required template
Then the entire file is rejected
And a popup message informs the user of the structural mismatch. The message is "The submited file has mismatched columns with the template CSV. Please download the template CSV and follow its structures to continue with the process."

Scenario: Duplicate Student ID detected — user reviews individually
Given a valid-structure CSV file is uploaded
When a row's Student ID matches an existing digital representation
And the user has not selected "Overwrite all"
Then the system prompts the user, for that specific record, to choose overwrite or not
And a side-by-side comparison view is displayed showing the existing version and the incoming version

Scenario: Duplicate Student ID — user chooses to overwrite
Given the comparison view is displayed for a duplicate Student ID
When the user confirms "Overwrite"
Then the existing digital representation is updated with the incoming record's data

Scenario: Duplicate Student ID — user chooses not to overwrite
Given the comparison view is displayed for a duplicate Student ID
When the user confirms "Do not overwrite"
Then the existing digital representation remains unchanged
And the incoming row is excluded from digital representation

Scenario: Overwrite all duplicates
Given a valid-structure CSV file contains one or more duplicate Student IDs
When the user selects "Overwrite all" before processing begins
Then all duplicate records are overwritten automatically
And no individual comparison prompts are shown

Scenario: Field-level validation failure
Given a row is being validated
When any of the following fields is invalid: DOB, Graduation year, National ID (hashed), Phone number
Then the row is excluded from digital representation
And the row is added to a consolidated error list containing: sequence number (STT), Student ID, and reason for invalidity

Scenario: Error list displayed on UI only
Given the CSV validation process has completed
When invalid rows exist
Then the consolidated error list (STT, Student ID, reason for invalidity) is displayed on the UI
And no downloadable file is generated for the error list

Scenario: Valid rows queued after validation
Given the CSV file has been validated
When valid rows are identified
Then valid rows are placed into a creation queue
And the Issuer Admin is prompted to confirm whether to proceed with digital representation

Scenario: Network/server failure during validation phase
Given the Issuer Admin has uploaded a CSV file for validation
When a network or server failure occurs before the user confirms creation
Then valid rows in the creation queue and the consolidated error list are both persisted
And the Issuer Admin does not need to re-upload the file once the system is restored

Scenario: User confirms creation, queue processed sequentially
Given valid rows are in the creation queue
When the Issuer Admin confirms to proceed
Then digital representations are created one by one in sequence, each with status "unclaimed"
And the queue is cleared as each record is successfully created

Scenario: User declines creation
Given valid rows are in the creation queue
When the Issuer Admin declines to proceed
Then the creation queue is cleared
And no digital representations are created

Scenario: Network/server failure during sequential creation
Given a digital representation is in progress from the queue
When a network or server failure occurs
Then already-created digital representations remain persisted
And unprocessed records remain in the queue

Scenario: Resume validation result after recovery
Given a persisted creation queue and error list exist from a prior interrupted session
When the Issuer Admin logs in again after the system is restored
Then the system displays the previous validation result (error list + pending queue)
And prompts the Issuer Admin to confirm whether to proceed with digital representations

Scenario: Completion notification after resumed processing
Given the queue has finished processing after a recovery
When the last record in the queue is created
Then the Issuer Admin is notified that the process completed successfully. The message is "Upload completed. X/Y records created successfully.", where X = number of successfully created records, Y = total records at the beginning.

> Ghi chú: giới hạn dung lượng CSV đã chốt lại là **20MB** (không phải 100MB như bản gốc), xem `lucidex_db_schema.md` mục 6.

## 1.6 — Manual check Pending

User Story:

As an Issuer Admin,

I want to review low-confidence claim requests in a queue that status is "Pending",

So that I can approve, reject, or request more information before confirming identity.

AC:

Scenario: Claim routed to review queue
Given a claim is submitted with ID verification confidence below 90%
When the claim is processed
Then it is automatically added to the Review Queue, ordered oldest first

Scenario: Single claim approval
Given the Issuer Admin opens a claim in the queue
When they approve it
Then the claim status becomes "claimed"
And the student is notified

Scenario: Bulk approval
Given multiple claims are selected in the queue
When the Issuer Admin approves them in bulk
Then all selected claims are confirmed simultaneously

Scenario: Claim rejection requires a reason
Given the Issuer Admin selects "Reject" on a claim
When no reason is entered
Then the rejection cannot be submitted
And a reason is required before the student is notified

Scenario: Request additional information
Given the Issuer Admin requests more information on a claim
When the student submits the requested details
Then the claim returns to the Review Queue for re-evaluation

## 1.7 — Display History

User Story:

As an Issuer Admin,

I want to search and filter the list of graduate records,

So that I can quickly locate and review the detailed status of any credential.

AC:

Scenario: Filter and search controls displayed
Given the Issuer Admin opens the Display History page
When the page loads
Then filter options for status, major, and graduation year are displayed
And a search input is displayed

Scenario: Filter records by criteria
Given the Issuer Admin is on the Display History page
When they select one or more filters (status, major, graduation year)
Then the record list updates to show only matching records

Scenario: Search records
Given the Issuer Admin is on the Display History page
When they enter a keyword in the search field
Then the record list updates to show only records where the keyword matches (case-insensitive, partial match) any of the following fields: Student ID, Full name, Major, Graduation year

Scenario: Record list summary view
Given the Display History page is loaded
When records are displayed
Then each row shows Student ID, Full name, major, and graduation year and status ("claimed" or "unclaimed")

Scenario: View record detail
Given the Issuer Admin is viewing the record list
When they click on a record
Then all credential details are displayed
And if the record is claimed, the claim method (National ID or auto university email) is displayed
And the claimed timestamp is displayed
And the unclaimed timestamp is displayed
And if the record is unclaimed, a reason code is displayed alongside the unclaimed timestamp, using one of the following predefined values:
| Reason code | Description |
| AWAITING_CLAIM | Digital representation created, owner has not claimed yet |
| CLAIM_REJECTED | Issuer rejected a submitted claim |

Scenario: No matching records
Given the Issuer Admin applies a filter or search
When no records match the criteria
Then a "No results found" message is displayed

## 1.8 — Revoke Credential

User Story:

As an Issuer Admin,

I want to revoke a credential with a documented reason,

So that all linked verifications reflect the revoked status accurately.

AC:

Scenario: Revoke requires a reason
Given the Issuer Admin selects "Revoke" on an active credential
When no reason is entered
Then the revocation cannot be confirmed

Scenario: Successful revocation
Given a valid reason is entered for revocation
When the Issuer Admin confirms the action
Then the credential status changes to "Revoked"
And all related Verified Links return "Credential revoked"
And the credential owner is notified
And the action is logged with actor, timestamp, and reason

## 1.9 — Monitoring Dashboard

User Story:

As an Issuer Admin,

I want to view verification trends, top employers, and top majors analytics,

So that I can monitor institutional credential activity and market insights.

AC:

Scenario: Verify Trends chart displayed
Given the Issuer Admin opens the Analytics Dashboard
When the page loads
Then a line chart titled "Verify Trends" is displayed
And it shows the number of verifications per month over time

Scenario: Top Employers chart displayed
Given the Issuer Admin opens the Analytics Dashboard
When the page loads
Then a horizontal bar chart titled "Top Employers" is displayed
And it ranks employers by number of verification requests, from highest to lowest

Scenario: Top Majors statistics displayed
Given the Issuer Admin opens the Analytics Dashboard
When the page loads
Then a "Top Majors" section is displayed
And it shows the count of verified credentials per major, ranked from highest to lowest

Scenario: All metrics reflect current data
Given the Analytics Dashboard is open
When any of the three sections (Verify Trends, Top Employers, Top Majors) is displayed
Then the data reflects the most recent available records at time of viewing.
