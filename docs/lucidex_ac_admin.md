# LUCIDEX — Acceptance Criteria: ADMIN PORTAL (US 4.1–4.6)

## 4.1 — View Pending Requests

User Story:

As an Admin,
I want to view all pending registration requests from Issuers and Organizations in one queue,
So that I can process them in a fair, predictable order.

AC:

Scenario: Pending requests split into two tabs
Given the Admin opens "Pending Requests"
When the page loads
Then two tabs are displayed: "Issuer" and "Organization"
And each tab shows only pending requests of that type

Scenario: Issuer tab displays pending Issuer requests
Given one or more Issuer registrations have status "pending review"
When the Admin opens the "Issuer" tab
Then all pending Issuer requests are listed, ordered oldest first
And each row shows institution name and submission date

Scenario: Organization tab displays pending Organization requests
Given one or more Organization registrations have status "pending review"
When the Admin opens the "Organization" tab
Then all pending Organization requests are listed, ordered oldest first
And each row shows organization name and submission date

Scenario: Empty state per tab
Given a tab has no requests with status "pending review"
When the Admin opens that tab
Then the empty state message "No pending requests." is displayed

Scenario: Tab shows pending count
Given a tab contains one or more pending requests
When the Admin views the Pending Requests page
Then each tab label displays the count of pending requests (e.g. "Issuer (5)")

## 4.2 — Request Detail

User Story:

As an Admin,
I want to open a pending request and view its full submitted information and attached documents,
So that I can make an informed approval decision.

AC:

Scenario: Full request detail displayed — Issuer
Given the Admin clicks on a pending Issuer request
When the detail view opens
Then it displays: institution name, tax code, registered address, legal representative's name, contact Gmail, contact phone, registrant's name
And it displays all attached documents

Scenario: Full request detail displayed — Verifier
Given the Admin clicks on a pending Verifier request
When the detail view opens
Then it displays: company name, 10-digit MSDN, registered address, legal representative's name, contact Gmail, contact phone, registrant's name, registrant's title
And it displays all attached documents
And if an authorization letter was submitted, it is also displayed

Scenario: Documents can be viewed in full
Given the request detail is open (Issuer or Verifier)
When the Admin clicks an attached document
Then the document opens in a viewer without leaving the request detail page

Scenario: Missing or corrupted document
Given an attached document fails to load
When the Admin attempts to view it
Then the message "This document could not be loaded." is shown

## 4.3 — Approve / Reject

User Story:

As an Admin,
I want to approve or reject a pending request after verifying its details against the attached documents,
So that only legitimate institutions and organizations gain access to the platform.

AC:

Scenario: Approve a request
Given the Admin has reviewed a request's details against its attached documents
When they select "Approve"
Then the request status changes to "approved"
And an email is sent to the registered contact email with the title "Your Lucidex Application Has Been Approved"
and body: "Dear [Registrant's name], we are pleased to inform you that your application for [Institution/Organization name] has been approved. Please find your invitation link below to complete account setup. Welcome to Lucidex."
And an invitation link is included in the email (per Issuer Flow 1.1)
And the account becomes usable as soon as onboarding is completed
And the request is no longer visible in the pending request list

Scenario: Reject a request with a reason
Given the Admin enters a reason and confirms "Reject"
When the rejection is submitted
Then the request status changes to "rejected"
And an email is sent to the registered contact email with the title "Update on Your Lucidex Application"
and body: "Dear [Registrant's name], thank you for your interest in Lucidex. After reviewing your application for [Institution/Organization name], we are unable to approve it at this time. Reason: [reason]. Thank you for your time and interest in Lucidex. We wish you all the best and look forward to the opportunity to review your application again in the future."
And a notification including the reason is sent to the applicant
And the action is logged with timestamp and reason
And the request is no longer visible in the pending request list

Scenario: Reject a request requires a reason
Given the Admin selects "Reject" on a request
When no reason is entered
Then the rejection cannot be submitted
And the message "A reason is required." is shown

Scenario: Approval and rejection decisions are immutable
Given a request has been approved or rejected
When the decision record is viewed
Then it cannot be edited or deleted by any user, including Admin

## 4.4 — System Dashboard

User Story:

As an Admin,
I want to see platform-wide metrics on verifications, active Issuers, active Organizations, and total students,
So that I can monitor the overall health and adoption of the platform.

AC:

Scenario: System dashboard summary displayed
Given the Admin opens the System Dashboard
When the page loads
Then it shows the following figures:
| Metric |
| Total verifications |
| Number of active Issuers |
| Number of active Organizations |
| Total credential owners |

Scenario: Dashboard reflects current data
Given a new Issuer/Organization is approved, or a new verification occurs
When the Admin returns to the dashboard
Then the displayed figures reflect the update within 30 seconds

Scenario: Empty platform state
Given no Issuers, Organizations, or verifications exist yet
When the Admin opens the System Dashboard
Then all figures display as 0

## 4.5 — Account Management

User Story:

As an Admin,
I want to suspend, lock, or reinstate active Issuer and Organization accounts,
So that I can respond to violations while preserving their underlying data.

AC:

Scenario: Find an active account
Given the Admin opens "Account Management"
When they type a keyword into the search bar and select account type filter (Issuer/Verifier/Owner)
Then matching active accounts are displayed in a table with columns: institution/organization name, account type, status, date registered
And the Admin can click a row to view full account detail

Scenario: Lock requires a reason
Given the Admin selects "Lock" on an active account
When no reason is entered
Then the action cannot be submitted
And the message "A reason is required." is shown

Scenario: Successful lock
Given the Admin enters a reason and confirms "Lock"
When the action is submitted
Then the account status changes to "locked"
And the account can no longer log in
And all existing data remains unchanged
And the action is logged with actor, timestamp, and reason

Scenario: Reinstate a locked account
Given the Admin selects "Reinstate" on a locked account
When they confirm the account is no longer in violation
Then the account status changes back to "active"
And login access is restored immediately
And the action is logged with actor and timestamp

Scenario: Locked account cannot log in
Given an account has status "locked"
When the account owner attempts to log in
Then access is denied
And the message "This account has been locked. Contact support for details." is shown

## 4.6 — System Audit Log

User Story:

As an Admin,
I want to search and export a complete log of every action taken by Issuers, Organizations, and Admins,
So that I can support compliance reviews and investigations.

AC:

Scenario: All platform events are logged
Given any action occurs on the platform
When the action completes
Then an entry is recorded showing the actor, action type, timestamp, and relevant details, according to the following reference table:

| Actor | Action Type | Description |
| Issuer | csv_uploaded | Issuer uploaded a graduate CSV file |
| Issuer | claim_approved | Issuer approved a pending claim (single/bulk) |
| Issuer | claim_rejected | Issuer rejected a claim, with a reason |
| Issuer | credential_revoked | Issuer revoked an issued credential with a reason |
| Owner | account_registered | Owner created a new account |
| Owner | claim_submitted | Owner submitted a claim request (email or CCCD) |
| Owner | verified_link_created | Owner created a new Verified Link |
| Owner | verified_link_revoked | Owner revoked an active Verified Link |
| Owner | consent_granted | Owner granted access to an organization |
| Owner | consent_revoked | Owner revoked previously granted access |
| Owner | account_data_deleted | Owner deleted specific data or entire account |
| Verifier | org_registered | Organization submitted a registration application |
| Verifier | credential_verified | Organization successfully verified a credential |
| Verifier | verification_denied | A verification attempt was denied |
| Admin | request_approved | Admin approved an Issuer/Verifier request |
| Admin | request_rejected | Admin rejected a request, with a reason |
| Admin | account_suspended | Admin suspended/locked an account, with a reason |
| Admin | account_reinstated | Admin restored access to a suspended account |

Scenario: Log entry includes actor-specific detail
Given an event has been logged
When the Admin views the entry
Then the "Detail" field is populated according to the following format
per action type:

| Action Type | Detail Field Format | Example |
| csv_uploaded | Institution name + file record count | "Institution: CTU, Records: 500" |
| claim_approved | Student ID + Institution name | "Student ID: B2012345, Institution: CTU" |
| claim_rejected | Student ID + Institution name + rejection reason | "Student ID: B2012345, Institution: CTU, Reason: Photo mismatch" |
| claim_info_requested | Student ID + Institution name | "Student ID: B2012345, Institution: CTU" |
| credential_revoked | Student ID + Institution name + revocation reason | "Student ID: B2012345, Institution: CTU, Reason: Academic fraud confirmed" |
| account_registered | Owner email (masked) | "Owner: a***@gmail.com" |
| claim_submitted | Student ID + claim method (Email OTP / CCCD) | "Student ID: B2012345, Method: CCCD" |
| verified_link_created | Link ID + credential Student ID | "Link ID: xK9mP2qR, Student ID: B2012345" |
| verified_link_revoked | Link ID | "Link ID: xK9mP2qR" |
| consent_granted | Organization name + credential Student ID | "Organization: FPT Software, Student ID: B2012345" |
| consent_revoked | Organization name + credential Student ID | "Organization: FPT Software, Student ID: B2012345" |
| account_data_deleted | Scope of deletion (specific item ID, or "Full account") | "Scope: Full account" or "Scope: Credential B2012345" |
| organization_registered | Organization name | "Organization: FPT Software" |
| credential_verified | Organization name + Student ID | "Organization: FPT Software, Student ID: B2012345" |
| verification_denied | Organization name + Link ID + denial reason | "Organization: FPT Software, Link ID: xK9mP2qR, Reason: Link expired" |
| request_approved | Institution/Organization name + applicant type | "Applicant: CTU (Issuer)" |
| request_rejected | Institution/Organization name + applicant type + rejection reason | "Applicant: CTU (Issuer), Reason: Invalid tax code" |
| account_suspended | Institution/Organization name + suspension reason | "Account: CTU (Issuer), Reason: Repeated data errors" |
| account_reinstated | Institution/Organization name | "Account: CTU (Issuer)" |

Scenario: Detail field is a single searchable string
Given a log entry has been created
When it is stored
Then the "Detail" field is saved as one plain-text string (not structured
JSON) so it can be matched by the audit log search function (Scenario:
Search the audit log)

Scenario: Sensitive data is masked in the Detail field
Given a log entry references an Owner's personal contact information
When the Detail field is generated
Then any email address is partially masked (e.g. "a***@gmail.com")
And no password, OTP, or raw national ID number ever appears in any
Detail field

Scenario: Search the audit log
Given the Admin opens "System Audit Log"
When they enter a keyword
Then matching entries are displayed, matched against actor name, institution/organization name, or Student ID

Scenario: Filter the audit log
Given the Admin is viewing the System Audit Log
When they filter by action type, actor type, or date range
Then only matching entries are displayed

Scenario: Combined search and filter
Given the Admin has entered a search keyword
When they also apply one or more filters (action type, actor type, date range)
Then only entries matching both the keyword and the filters are displayed

Scenario: No matching entries
Given the Admin applies a search or filter
When no entries match the criteria
Then the message "No matching audit log entries found." is displayed

Scenario: Export the audit log
Given the Admin has applied a search or filter (or none)
When they select "Export"
Then a file containing the currently filtered results is downloaded in CSV format

Scenario: Audit log entries are immutable
Given the System Audit Log contains one or more entries
When the log is viewed
Then no entry can be edited or deleted by any user, including Admin
