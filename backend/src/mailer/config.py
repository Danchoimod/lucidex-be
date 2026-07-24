"""Email-template registry."""

from typing import Final

from src.mailer.constants import EmailTemplate

APPLICATION_REVIEW_SLA_DAYS: Final = "3–5"
EMAIL_TEMPLATE_CONFIGS: Final[dict[EmailTemplate, tuple[str, str]]] = {
    EmailTemplate.OWNER_REGISTER_OTP: (
        "Activate your Lucidex account",
        "owner/register_otp.html",
    ),
    EmailTemplate.OWNER_RESET_PASSWORD_OTP: (
        "Reset your Lucidex password",
        "owner/reset_password_otp.html",
    ),
    EmailTemplate.OWNER_LOGIN_OTP: (
        "Your Lucidex login code",
        "owner/login_otp.html",
    ),
    EmailTemplate.OWNER_WELCOME: (
        "Chào mừng bạn đến với Lucidex!",
        "owner/welcome.html",
    ),
    EmailTemplate.ORGANIZATION_REGISTER_OTP: (
        "Activate your Lucidex organization account",
        "organization/register_otp.html",
    ),
    EmailTemplate.ORGANIZATION_RESET_PASSWORD_OTP: (
        "Reset your Lucidex organization password",
        "organization/reset_password_otp.html",
    ),
    EmailTemplate.ORGANIZATION_LOGIN_OTP: (
        "Your Lucidex organization login code",
        "organization/login_otp.html",
    ),
    EmailTemplate.ISSUER_APPLICATION_RECEIVED: (
        "Received Lucidex registration application for {{ organization_name }}",
        "organization/issuer_application_received.html",
    ),
    EmailTemplate.VERIFIER_APPLICATION_RECEIVED: (
        "Received Lucidex registration application for {{ institution_name }}",
        "organization/verifier_application_received.html",
    ),
    EmailTemplate.INSTITUTION_INVITE: (
        "Complete setup for your Lucidex organization account",
        "organization/invite.html",
    ),
    EmailTemplate.APPLICATION_REJECTED: (
        "Update on Your Lucidex Application",
        "organization/application_rejected.html",
    ),
}
