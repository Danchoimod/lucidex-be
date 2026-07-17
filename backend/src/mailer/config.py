"""Email-template registry."""

from typing import Final

from src.mailer.constants import EmailTemplate

TemplateConfig = tuple[str, str]

EMAIL_TEMPLATE_CONFIGS: Final[dict[EmailTemplate, TemplateConfig]] = {
    EmailTemplate.OWNER_REGISTER_OTP: (
        "Activate your Lucidex account",
        "owner/register_otp.html",
    ),
    EmailTemplate.OWNER_RESET_PASSWORD_OTP: (
        "Reset your Lucidex password",
        "owner/reset_password_otp.html",
    ),
    EmailTemplate.ORGANIZATION_REGISTER_OTP: (
        "Activate your Lucidex organization account",
        "organization/register_otp.html",
    ),
    EmailTemplate.ORGANIZATION_RESET_PASSWORD_OTP: (
        "Reset your Lucidex organization password",
        "organization/reset_password_otp.html",
    ),
}
