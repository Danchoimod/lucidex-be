# LUCIDEX — Acceptance Criteria: OWNER PORTAL (US 2.1–2.12)

## 2.1 — Register & Login

As a prospective Credential Owner,
I want to register and log in using email/password or a third-party OAuth provider,
So that I can securely access my portal account.

AC:

Scenario: Submit registration form with valid password
Given an upcoming Owner accesses the Registration page
When they enter an email, a password, and a matching confirm password
And the password meets the following requirements:
| Requirement |
| At least 8 characters |
| At least 1 uppercase letter |
| At least 1 lowercase letter |
| At least 1 number |
| At least 1 special character |
Then an OTP is sent to the entered email
And the Owner is prompted to enter the OTP

Scenario: Password and confirm password do not match
Given the Owner is filling out the Registration form
When the password and confirm password fields do not match
Then the error message "Password and Confirm Password do not match." is displayed
And no OTP is sent

Scenario: Registration with weak password
Given the entered password fails one or more security requirements
When the registration form is submitted
Then the error message "Password must contain at least 8 characters, 1 uppercase
letter, 1 lowercase letter, 1 number, and 1 special character." is displayed
And no OTP is sent

Scenario: Registration with an already-registered email
Given the entered email is already associated with an existing account
When the registration form is submitted
Then the error message "This email is already registered." is displayed
And no OTP is sent

Scenario: Successful OTP verification
Given an OTP has been sent to the entered email
When the Owner enters the correct OTP
Then an account is created
And they are redirected to the Credential Owner Portal home page

Scenario: Incorrect OTP entered
Given an OTP has been sent to the entered email
When the Owner enters an incorrect OTP
Then the error message "Invalid OTP. Please try again." is displayed
And the account is not created

Scenario: OTP expired
Given an OTP has been sent to the entered email
When the Owner attempts verification after the OTP expiry window
Then the error message "OTP has expired. Please request a new code." is displayed
And the Owner can request a new code

Scenario: Successful registration via third-party OAuth
Given a prospective Owner accesses the Registration page
When they choose to register using a third-party OAuth provider (e.g. Google)
and complete authentication
Then an account is created using the identity returned by the OAuth provider
And the platform does not store or manage a password for this account
And they are redirected to the Credential Owner Portal home page

Scenario: Successful login
Given a registered Owner enters a correct email and password
When they submit the login form
Then they are granted access to the Credential Owner Portal

Scenario: Login with invalid credentials
Given an incorrect email or password is entered
When the login form is submitted
Then the error message "Invalid login credentials." is shown
And no session is created

## 2.2 — Notification Center

As a Credential Owner,
I want to receive real-time notifications about my claims, credentials, and link activity,
So that I stay informed without needing to check manually.

AC:

Scenario: Notification on claim submitted
Given the owner submits a claim request
When the OTP or eKYC step is successfully initiated
Then a notification with the message "Your claim request has been submitted."
is created and shown via the bell icon within 1 minute

Scenario: Notification on claim routed to review
Given the owner's claim has a verification confidence below 90%
When the claim is routed to the Issuer's Review Queue
Then a notification with the message "Your claim is under review by [Issuer Institution]." is created and shown via the bell icon within 1 minute

Scenario: Notification on claim approved
Given the owner's claim is approved (auto or manual)
When the claim status becomes "claimed"
Then a notification with the message "Your credential has been successfully claimed."
is created and shown via the bell icon within 1 minute

Scenario: Notification on claim rejected
Given the owner's claim is rejected by the Issuer
When the rejection is confirmed
Then a notification with the message "Your claim was rejected. Reason: [reason]."
is created and shown via the bell icon within 1 minute

Scenario: Notification on verified link viewed
Given the owner has an active Verified Link
When someone successfully views the credential through that link
Then a notification with the message "[Organization name] viewed your credential
via link [link ID]." is created

Scenario: Notification on denied access attempt
Given someone attempts to access an expired or revoked Verified Link
When the access attempt is denied
Then a notification with the message "A denied access attempt was made on
link [link ID]." is created

Scenario: Tapping a notification navigates to the relevant screen
Given the owner has one or more notifications
When they tap a notification
Then they are taken directly to the related claim, credential, or link detail

Scenario: Unread notification indicator
Given one or more notifications have not been viewed
When the owner views the bell icon
Then an unread count badge is displayed

Scenario: No notifications state
Given the owner has no notifications
When they open the Notification Center
Then the empty state message "You have no notifications yet." is displayed

(Owner can also clear all notifications)

## 2.3 — Claim via University Email (.edu)

As a credential owner with an active university email,
I want to claim my degree by selecting my institution and providing my student ID and university email, verified via a one-time OTP,
So that I can verify ownership of my credential without a physical document.

AC:

Scenario: All fields required before submission
Given the owner is on the Claim Degree form
When one or more of the following fields are left empty: Institution,
Student ID, University email
Then the "Submit" button remains disabled
And the missing fields are highlighted

Scenario: Institution must be selected from the dropdown
Given the owner is on the Claim Degree form
When they attempt to submit without selecting an Institution from the dropdown
Then the error message "Please select an Institution." is shown
And the form is not submitted

Scenario: University email must be a well-formed email address
Given the owner enters a university email that is not a valid email format
When they attempt to submit the form
Then the error message "Please enter a valid email address." is shown
And the form is not submitted

Scenario: Student ID must exist in the database
Given the owner enters a Student ID that does not exist in the database
for the selected Institution
When they submit the claim request
Then the generic error message "We couldn't verify this information. Please check your Institution, Student ID, and university email." is shown
And it does not disclose whether the Student ID exists in the system

Scenario: University email does not match the existing record
Given the owner enters a Student ID that exists but a university email
that does not match the record on file
When they submit the claim request
Then the same generic error message as "We couldn't verify this infomation. Please check your Institution, Student ID, and university email." is shown
And it does not disclose whether the Student ID exists in the system

Scenario: Successful lookup and OTP dispatch
Given the owner chooses an Institution from the dropdown of verified institutions
And enters a Student ID that exists in the database for that Institution
And enters a university email in valid format that matches the record
When they submit the claim request
Then an OTP is sent to the entered university email
And the OTP is valid for 5 minutes

Scenario: Successful claim with correct OTP
Given an OTP has been sent and is still valid
When the owner enters the correct OTP
Then the claim is marked "claimed"
And the credential appears in "My Credentials"

Scenario: Incorrect OTP
Given an OTP has been sent
When the owner enters an incorrect code
Then the error message "Invalid OTP. Please try again." is shown
And they may retry up to 5 times

Scenario: OTP expired
Given more than 5 minutes have passed since the OTP was sent
When the owner attempts to verify
Then the error message "OTP has expired. Please request a new code." is shown
And the owner can request a new one

Scenario: Resend rate limit
Given the owner has requested a resend 3 times within 10 minutes
When they request another resend
Then the request is blocked
And the message "Too many resend attempts. Please try again in 10 minutes."
is displayed

## 2.4 — Claim via CCCD (Fallback)

As a credential owner without access to my university email,
I want to claim my degree using eKYC verification with my national ID and a selfie,
So that I can still prove ownership of my credential.

AC:

Scenario: Guided capture instructions shown
Given the owner selects "Claim via CCCD"
When the capture screen loads
Then the following instructions are displayed before capture begins:
| Step | Instruction |
| 1 | Place your ID card on a dark, plain, non-reflective background |
| 2 | Ensure even lighting with no shadows or glare on the card surface |
| 3 | Position the card so all 4 corners are fully visible in the frame |
| 4 | Hold the camera steady and avoid blur |
| 5 | Capture the front side first, then the back side |
| 6 | For the selfie: face the camera directly in a well-lit area, |
| | remove glasses/hat/mask, and keep a neutral expression |
And user must take live photos for front and back CCCD images and selfie

Scenario: Successful eKYC verification
Given the owner uploads front and back CCCD images and a selfie
When eKYC processing evaluates the following criteria:
| Criterion | Threshold |
| OCR field match | Name and DOB extracted match the issuer's |
| | record with >= 90% text similarity |
| National ID hash match | Hash of extracted ID number matches |
| | national_id_hash on file (if provided) |
| Face match score | >= 90% similarity between selfie and ID photo |
| Liveness detection | Passed (real person confirmed, not a photo |
| | of a photo or a video replay) |
And the combined confidence score is 90% or higher
Then the claim is automatically approved and marked "claimed"
And the raw CCCD images and selfie are deleted immediately, retaining only
the hash, match result, and timestamp
And the message "Your credential has been successfully claimed." is shown

Scenario: Low-confidence match shows warning with retry option
Given eKYC processing completes with a combined confidence score below 90%
When the result is returned
Then a warning screen is displayed with the message "Your identity
verification confidence is low. Your claim will need manual confirmation
from [Issuer Institution], which may take longer than usual."
And two options are shown: "Scan Again" and "Confirm"

Scenario: Owner chooses to scan again after low-confidence result
Given the low-confidence warning screen is displayed
When the owner selects "Scan Again"
Then they are returned to the guided capture screen
And the previous low-confidence attempt is discarded
And they must retake the CCCD and selfie photos

Scenario: Owner accepts and proceeds to review queue
Given the low-confidence warning screen is displayed
When the owner selects "Confirm"
Then the claim is routed to the Issuer's Review Queue with status "pending"
And the owner is notified with the message "Your claim is under review by
[Issuer Institution]."

Scenario: Retry limit for low-confidence scans
Given the owner has selected "Scan Again" 3 times consecutively, each
resulting in a confidence score below 90%
When they attempt to scan again a 4th time
Then the "Scan Again" option is disabled
And the message "Please proceed with manual review, or try again later."
is shown with only the "Confirm" option available

Scenario: Unreadable or invalid image submitted
Given an uploaded CCCD image fails basic image-quality checks:
| Check | Failure condition
| Sharpness | Image is too blurry for OCR to extract text
| Completeness | One or more of the 4 corners is cropped out
| Glare/obstruction | Glare or shadow obscures key fields (ID number, name, DOB)
| File integrity | File is corrupted or fails to load
When eKYC processing attempts to extract data
Then the message "We couldn't read your ID clearly. Please retake the photo."
is shown
And no claim attempt is recorded until a valid image is submitted

Scenario: Liveness check fails
Given the selfie fails the liveness detection check because one of the
following is detected:
| Failure reason |
| Selfie appears to be a photo of a photo (screen/print) |
| Selfie appears to be a pre-recorded video replay |
| No face detected in the frame |
When eKYC processing completes
Then the claim is rejected at this step
And the message "We couldn't verify you're a live person. Please try again."
is shown

## 2.5 — Credential List & Detail

As a Credential Owner,
I want to view a list of my claimed credentials and see each one rendered as a digital degree,
So that I can review and present my academic achievements.

AC:

Scenario: View credential list
Given the owner has one or more claimed credentials
When they open "My Credentials"
Then each credential is listed as a card showing student ID, full name, degree type, major, graduation classification and graduation year

Scenario: Empty state
Given the owner has no claimed credentials
When they open "My Credentials"
Then the empty state message "You don't have any claimed credentials yet." is displayed

Scenario: View digital degree detail
Given the owner taps a credential in the list
When the detail view opens
Then it renders as a digital degree formatted to resemble the physical certificate layout, including full name, major, degree type, graduation year, and classification
And all academic fields are read-only

Scenario: Issuer verification mark displayed on the digital degree
Given a credential was issued by an Issuer
When its detail is viewed
Then the digital degree displays an issuer verification mark (e.g. digital seal/signature) showing "Verified by [Issuer name]"
And displays the issuance timestamp

Scenario: Revoked credential is visually distinguished
Given a credential has been revoked by the Issuer
When its detail is viewed
Then the digital degree is displayed with a "Revoked" overlay
And the issuer verification mark is not shown

## 2.6 — View / Edit Profile

As a Credential Owner,
I want to view and update my personal profile information,
So that my account details stay accurate and current.

AC:

Scenario: Profile displays personal information fields
Given the owner opens their Profile
When the page loads
Then the following personal fields are displayed:
| Field | Editable |
| Avatar | Yes |
| Full name | Yes |
| Phone number | Yes |
| Login email | No |
| Date of birth | No |

Scenario: Editable fields can be updated
Given the owner opens their Profile
When they update their avatar, full name, or phone number and save
Then the changes are persisted
And the confirmation message "Your profile has been updated." is shown

Scenario: Invalid full name
Given the owner clears the Full name field or enters only special
characters/numbers
When they attempt to save
Then the validation error "Please enter a valid name." is shown
And the change is not saved

Scenario: Invalid phone number format
Given the owner enters a phone number in an invalid format
When they attempt to save
Then the validation error "Please enter a valid phone number." is shown
And the change is not saved

Scenario: Invalid avatar file
Given the owner uploads a file that is not a supported image format
(.jpg, .png) or exceeds 5 MB
When they attempt to save
Then the validation error "Please upload a valid image (JPG or PNG, max 5MB)."
is shown
And the change is not saved

## 2.7 — Create / Revoke Verified Link

As a Credential Owner,
I want to create and revoke shareable verified links for my credentials,
So that I can control who can access my credential and for how long.

AC:

Scenario: Create a verified link
Given the owner selects one credential and only one consent type
When they confirm link creation
Then a signed URL is generated
And a one-time OTP is generated and tied to that link
And both the URL and OTP are shown for the owner to share

Scenario: View link list
Given the owner has created one or more links
When they open "My Links"
Then each link is shown with its status: active, expired, or revoked
And consent type is shown

Scenario: Revoke a link
Given the owner selects an active link
When they confirm "Revoke"
Then the link status changes to "Revoked" immediately
And its OTP is invalidated immediately
And any subsequent access attempt shows the message "Access revoked."

Scenario: Expired link access
Given a link has passed its consent expiration
When someone attempts to use it
Then access is denied with the message "This link has expired."

## 2.8 — Consent Settings

As a Credential Owner,
I want to choose a default consent type for sharing my credentials,
So that I can control how my information is accessed without configuring it every time.

AC:

Scenario: Consent type options are explained
Given the owner opens Consent Settings
When the page loads
Then each consent type is displayed with its description:
| Type | Description |
| One-time | The link can be viewed exactly once, then it |
| | expires automatically. |
| Per-request | Each time someone tries to view your credential, |
| | you'll be asked to approve or decline. |
| Organization-level | Approve once for a specific organization — they |
| | can view your credential repeatedly afterward |
| | without asking again. |
| Time-bound | The link stays valid for a set period (24 hours, |
| | 7 days, 30 days, or permanent), viewable any number |
| | of times until it expires. |

Scenario: Select a default consent type
Given the owner opens Consent Settings
When they select one of: One-time, Per-request, Organization-level, or Time-bound
Then the selection is saved as their default consent type

Scenario: Time-bound requires a duration
Given the owner selects "Time-bound"
When no duration is selected
Then the setting cannot be saved
And the message "Please select a duration: 24 hours, 7 days, 30 days, or
permanent." is shown

Scenario: Organization-level requires selecting an organization
Given the owner selects "Organization-level" as the consent type for a link
When no organization is selected from the approved organizations list
Then the setting cannot be saved
And the message "Please select an organization for this consent type." is shown

Scenario: Default applies to new links only
Given the owner changes their default consent type
When a new link is created afterward
Then the new link uses the updated default
And previously created links remain unaffected

## 2.9 — Trusted Organizations

As a Credential Owner,
I want to search for and add approved organizations to a trusted list,
So that they can verify my credential without requiring my approval each time.

AC:

Scenario: Search shows only approved organizations
Given the owner types a keyword into the organization search field
When results are returned
Then only organizations with an approved Verifier status matching the
keyword are shown
And results appear in a dropdown list with a checkbox next to each
organization

Scenario: No matching organizations found
Given the owner types a keyword with no matching approved organizations
When the search completes
Then the dropdown displays "No matching organizations found."

Scenario: Select multiple organizations via checkboxes
Given the search dropdown is displaying results
When the owner checks the checkbox next to one or more organizations
Then each selected organization is marked as checked
And the owner can continue searching and checking additional organizations
before confirming

Scenario: Add selected organizations to trusted list
Given the owner has checked one or more organizations in the dropdown
When they confirm "Add"
Then all checked organizations are added to the trusted list
And each added organization can verify the owner's credential without a
per-request prompt
And the message "[N] organization(s) have been added to your trusted
organizations." is shown

Scenario: Trusted list is paginated
Given the owner's trusted organizations list contains more than 10 entries
When they open the Trusted Organizations page
Then the list is displayed in pages of 10 entries each
And pagination controls are shown to navigate between pages

Scenario: Remove a trusted organization
Given an organization is on the owner's trusted list
When the owner removes it
Then the removal takes effect immediately
And the message "[Organization name] has been removed from your trusted
organizations." is shown
And future verification requests from that organization require explicit
consent again

## 2.10 — Audit Log

As a Credential Owner,
I want to view an immutable log of all access attempts to my credentials,
So that I can track who viewed or attempted to view my information.

AC:

Scenario: Successful view is logged
Given someone accesses a credential via a Verified Link
When the access occurs
Then an entry is recorded showing the viewer/organization, link used, timestamp,
and consent type

Scenario: Denied access attempts are logged
Given someone attempts to access an expired or revoked link
When the attempt is made
Then a "DENIED" entry is recorded with the reason and timestamp

Scenario: Audit log entries are immutable
Given the audit log contains one or more entries
When the log is viewed
Then no entry can be edited or deleted by any user

## 2.11 — Personal Dashboard

As a Credential Owner,
I want to view a summary dashboard of my credentials, active links, and verification activity,
So that I can monitor my credential usage at a glance.

AC:

Scenario: Dashboard summary displayed
Given the owner opens their personal dashboard
When the page loads
Then it shows the following summary figures:
| Metric | Description |
| No. Credential | Total number of credentials claimed |
| Verified Link | Number of currently active Verified Links |
| People view verified | Total number of successful views by viewers |

Scenario: Verification timeline displayed
Given verification events have occurred
When the dashboard loads
Then a chronological timeline of verification events is shown, each entry
including the viewer/organization, outcome (verified or denied), and timestamp

Scenario: Empty dashboard state
Given the owner has no credentials, links, or verification events yet
When they open their personal dashboard
Then all figures display as 0
And the timeline shows the message "No verification activity yet."

Scenario: Dashboard reflects current data
Given a new verification event occurs
When the owner returns to the dashboard
Then the displayed figures reflect the update within 5 minutes

## 2.12 — Data Deletion

As a Credential Owner,
I want to delete a specific credential/link or my entire account with a recovery window,
So that I can manage my data while having a safeguard against accidental deletion.

AC:

Scenario: Delete a specific credential or link
Given the owner selects a specific credential or link to delete
When they confirm the deletion
Then that item is marked as deleted and no longer appears in the owner's records
And the item can be restored within 3 days
And the message "Deleted successfully. This can be restored within 3 days." is shown

Scenario: Restore a deleted credential or link within 3 days
Given a credential or link was deleted less than 3 days ago
When the owner chooses to restore it
Then the item is restored and reappears in the owner's records

Scenario: Credential or link permanently deleted after 3 days
Given a credential or link has been marked as deleted for more than 3 days
When the retention period expires
Then the item is permanently deleted
And it can no longer be restored

Scenario: Delete entire account
Given the owner selects "Delete account"
When the confirmation warning "Deleting your account is permanent after 30 days. You will lose access, and all active Verified Links will stop working immediately. You can restore your account within 30 days." is shown
And they confirm the action
Then the account is marked as deleted
And all active Verified Links immediately become invalid
And the account can be restored within 30 days

Scenario: Restore account within 30 days
Given the account was deleted less than 30 days ago
When the owner logs in and chooses to restore the account
Then the account is reactivated
And previously invalidated Verified Links are not automatically restored

Scenario: Account permanently deleted after 30 days
Given the account has been marked as deleted for more than 30 days
When the retention period expires
Then all personal data is permanently deleted
And the deletion cannot be reversed by the owner or by Admin.
