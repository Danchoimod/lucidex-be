# LUCIDEX — Acceptance Criteria: VERIFIER PORTAL (US 3.0–3.7)

## 3.0 — Verifier Registration

User Story:

As an upcoming Verifier,
I want to submit my registration through a dedicated form,
So that I can apply to verify credentials without relying on email-based submission.

AC:

Scenario: Successful form submission
Given an upcoming Verifier accesses the Verifier Registration page
When they fill in all required fields:
| Field |
| Organization name |
| Tax code |
| Registered address |
| Legal representative's name |
| Contact Gmail |
| Contact phone |
| Registrant's name |
And they can upload a business registration certificate
And they submit the form
Then the application is created with status "pending review"
And a confirmation message "Your registration application has been submitted successfully and is pending review." is shown to the registrant

Scenario: Submission with missing required fields
Given the Verifier is filling out the Registration form
When one or more required fields are left empty, or the business registration certificate is not uploaded
Then the form cannot be submitted
And the missing fields are highlighted
And a warning message is shown listing the specific missing field(s).
The template message is "Please fill in the following required field(s): [Field name 1], [Field name 2]."

Scenario: Invalid field format
Given the Verifier enters data in a format that does not match the required rules
When they attempt to submit the form
Then a validation error is shown next to each invalid field, specifying
the expected format:
| Field | Required format |
| Organization name | Text, 3–200 characters |
| Tax code / MSDN | Exactly 10 digits |
| Registered address | Text, non-empty |
| Legal representative's name | Text, letters only |
| Contact Gmail | Valid email format (e.g. name@gmail.com) |
| Contact phone | 10-digit Vietnamese phone number |
| Registrant's name | Text, letters only |
| Registrant's title | Text, non-empty |
And the form is not submitted

Scenario: Application enters Admin review queue
Given a registration form has been successfully submitted
When the application is created
Then it appears in the Admin's approval queue (Flow 4.1–4.3), under the "Verifier" tab, with status "pending review"

## 3.1 — Onboarding & Account Provisioning

User Story:

As an approved Verifier,
I want to receive a one-time invite link via my registered contact email,
So that I can set up my own admin account without depending on a specific email domain.

AC:

Scenario: Invite link sent after Admin approval
Given a Verifier application has been approved by the Admin
When the approval is confirmed
Then an invitation email with the subject "Verifier Account Setup Invitation" is sent to the registered contact email
And the link is valid for one single use only

Scenario: Verifier sets up account with valid password
Given the Verifier clicks a valid, unused invite link
When they submit a new username, a password, and a matching confirm password
And the password meets the minimum security requirements
| Requirement |
| At least 8 characters |
| At least 1 uppercase letter |
| At least 1 lowercase letter |
| At least 1 number |
| At least 1 special character |
Then the account is created
And the user is redirected to mandatory 2FA setup

Scenario: Password and confirm password do not match
Given the Verifier clicks a valid, unused invite link
When they enter a password and a confirm password that do not match
Then the error message "Password and confirm Password do not match." is displayed
And the account is not created

Scenario: Password does not meet security requirements
Given the Verifier clicks a valid, unused invite link
When they enter a password that fails one or more security requirements
Then the error message "Password must contain at least 8 characters, 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character." is displayed
And the account is not created

Scenario: Reused invite link
Given an invite link was already used
When the Verifier attempts to access it
Then the error message "This invitation link has already been used." is displayed
And no account is created

Scenario: One account per Verifier
Given a Verifier has already completed account setup
When a second invite is attempted for the same approved application
Then no additional account is created
And the existing account remains the sole account for that Verifier

## 3.1b — Login & 2FA

User Story:

As a Verifier,
I want to log in using my username, password, and 2FA,
So that only verified staff can access candidate verification data.

AC:

Scenario: Successful login
Given a registered Verifier with valid credentials and 2FA already configured
When they enter correct username and password
And they complete the 2FA challenge successfully
Then they are granted access to the Verifier Portal home page

Scenario: Login fails without 2FA
Given valid username and password are entered
When 2FA verification is not completed
Then access to the Portal is denied
And the message "Two-factor authentication is required to continue." is shown

Scenario: Invalid credentials
Given incorrect username or password is entered
When the Verifier attempts to log in
Then the error message "Invalid login username or password." is shown
And no session is created

Scenario: Default 2FA setup via email OTP
Given the Verifier has completed account setup
When the 2FA setup popup appears
Then an OTP is automatically sent to the registered contact email
And the message "A verification code has been sent to your registered email." is shown
And the Verifier can enter the OTP to activate 2FA

Scenario: Switch to SMS method
Given the 2FA setup popup is displayed with email as the default method
When the Verifier selects "Switch to SMS"
Then an OTP is sent to the phone number registered at sign-up
And the message "A verification code has been sent to your registered phone number." is shown
And the Verifier can enter the OTP to activate 2FA via SMS

Scenario: Incorrect OTP entered
Given an OTP has been sent (via email or SMS)
When the Verifier enters an incorrect code
Then the error message "Invalid OTP. Please try again." is displayed
And 2FA is not activated

Scenario: OTP expired
Given an OTP has been sent (via email or SMS)
When the Verifier attempts to verify after the OTP expiry window
Then the error message "OTP has expired. Please request a new code." is displayed
And the Verifier can request a new OTP

Scenario: 2FA enforced on every login
Given 2FA has been activated
When the Verifier logs in at any time
Then 2FA verification is required and cannot be skipped
And access to the Portal is granted only after successful 2FA verification
And upon success, the message "Login successful. Welcome back." is shown

## 3.2 — Status Tracking

User Story:

As an applicant Verifier,
I want to check the status of my registration application,
So that I know whether I can proceed or need to take further action.

AC:

Scenario: View pending status
Given the Verifier's application has status "pending review"
When they open "Registration Status"
Then the status "Pending" is displayed with the message "Your application is being reviewed."

Scenario: View approved status
Given the Verifier's application has been approved
When they open "Registration Status"
Then the status "Approved" is displayed
And they have full access to Verifier Portal features

Scenario: View rejected status with reason
Given the Verifier's application has been rejected
When they open "Registration Status"
Then the status "Rejected" is displayed along with the reason provided by Admin and timestamp

Scenario: Resubmit after rejection
Given the Verifier's application has status "Rejected"
When they correct the information and submit again
Then a new application is created with status "pending review"
And it appears in the Admin's approval queue as a new entry

## 3.3 — Verify Single Link

User Story:

As a Verifier,
I want to open a candidate's Verified Link and confirm it using the accompanying OTP,
So that I can view a candidate's authentic credential.

AC:

Scenario: Open a verification link
Given the Verifier has received a signed URL from a candidate
When they open the URL directly, or paste it into the "Verify Credential" field
Then they are taken to a page prompting for the OTP

Scenario: Successful verification with correct OTP
Given the Verifier is on the OTP prompt page for a valid, unexpired link
When they enter the correct OTP
Then the credential is unlocked, and all related information of the given credential is shown
And an entry is recorded in Verification History

Scenario: Incorrect OTP
Given the Verifier is on the OTP prompt page
When they enter an incorrect OTP
Then access is denied
And the message "Incorrect OTP. Please try again." is shown
And they may retry up to 3 times

Scenario: OTP retry limit reached
Given the Verifier has entered an incorrect OTP 3 times
When they attempt a 4th time
Then further attempts are blocked for 10 minutes
And the message "Too many incorrect attempts. Please try again later." is shown

Scenario: Expired or revoked link
Given the link has expired or been revoked by the credential owner
When the Verifier attempts to access it
Then the message "Link no longer valid. Please request a new link from the candidate." is shown
And no OTP prompt is presented

## 3.4 — Dashboard

User Story:

As a Verifier,
I want to view verification counts, history, and trends,
So that I can monitor my organization's verification activity.

AC:

Scenario: Dashboard summary displayed
Given the Verifier opens the Dashboard
When the page loads
Then it shows the total number of verifications and the all-time verification history

Scenario: Monthly bar chart displayed
Given verification events exist across multiple months
When the Dashboard loads
Then a bar chart shows the number of verifications per month

Scenario: Pie chart displayed
Given verification events exist
When the Dashboard loads
Then a pie chart shows the breakdown of verifications by institution
or by result (verified/denied)

Scenario: Empty dashboard state
Given the Verifier has no verification events yet
When they open the Dashboard
Then all figures display as 0
And the message "No verification activity yet." is shown

## 3.5 — Audit Export

User Story:

As a Verifier,
I want to export my verification history in my preferred format,
So that I can use it as internal compliance documentation.

AC:

Scenario: Export format selection
Given the Verifier opens Verification History and selects "Export"
When the export dialog appears
Then they are prompted to choose one of two formats: CSV or PDF

Scenario: Export as CSV
Given the Verifier selects "CSV" as the export format
When they confirm the export
Then a CSV file containing the full verification history is downloaded

Scenario: Export as PDF
Given the Verifier selects "PDF" as the export format
When they confirm the export
Then a PDF file containing the full verification history is downloaded

Scenario: Only one format selectable per export
Given the Verifier is on the export dialog
When they select one format
Then the other format option is deselected
And only the selected format is included in that export

## 3.6 — Quota & Plan

User Story:

As a Verifier,
I want to view my organization's current plan and usage against quota,
So that I can track how many verifications I have remaining before the next reset.

(AC chưa xác định — scope chưa chốt. Xem `lucidex_db_schema.md` mục 9 — placeholder tối thiểu đã có ở `organizations.verifier_profile.plan`. Khi implement, để API trả dữ liệu tĩnh/mock và đánh dấu `# TODO: chờ chốt AC US 3.6`.)

## 3.7 — Upgrade Plan

User Story:

As a Verifier,
I want to compare and upgrade my organization's plan with automatic payment,
So that I can increase my verification quota when needed.

(AC chưa xác định — scope chưa chốt, để bổ sung sau. Xử lý tương tự US 3.6 khi implement.)
