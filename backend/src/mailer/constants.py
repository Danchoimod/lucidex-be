"""Email templates supported by the mailer."""

from enum import StrEnum


class EmailTemplate(StrEnum):
    REGISTER_OTP = "REGISTER_OTP"
    RESET_PASSWORD_OTP = "RESET_PASSWORD_OTP"
