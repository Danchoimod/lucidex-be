"""Email-template registry."""

from typing import Final

from src.mailer.constants import EmailTemplate

APPLICATION_REVIEW_SLA_DAYS: Final = "3–5"
EMAIL_TEMPLATE_CONFIGS: Final[dict[EmailTemplate, tuple[str, str]]] = {
    EmailTemplate.OWNER_REGISTER_OTP: (
        "Kích hoạt tài khoản Lucidex của bạn",
        "owner/register_otp.html",
    ),
    EmailTemplate.OWNER_RESET_PASSWORD_OTP: (
        "Đặt lại mật khẩu Lucidex của bạn",
        "owner/reset_password_otp.html",
    ),
    EmailTemplate.OWNER_LOGIN_OTP: (
        "Mã đăng nhập Lucidex của bạn",
        "owner/login_otp.html",
    ),
    EmailTemplate.ORGANIZATION_REGISTER_OTP: (
        "Kích hoạt tài khoản tổ chức Lucidex",
        "organization/register_otp.html",
    ),
    EmailTemplate.ORGANIZATION_RESET_PASSWORD_OTP: (
        "Đặt lại mật khẩu tài khoản tổ chức Lucidex",
        "organization/reset_password_otp.html",
    ),
    EmailTemplate.ORGANIZATION_LOGIN_OTP: (
        "Mã đăng nhập tài khoản tổ chức Lucidex",
        "organization/login_otp.html",
    ),
    EmailTemplate.ISSUER_APPLICATION_RECEIVED: (
        "Đã nhận hồ sơ đăng ký Lucidex của {{ organization_name }}",
        "organization/issuer_application_received.html",
    ),
    EmailTemplate.VERIFIER_APPLICATION_RECEIVED: (
        "Đã nhận hồ sơ đăng ký Lucidex của {{ institution_name }}",
        "organization/verifier_application_received.html",
    ),
}
