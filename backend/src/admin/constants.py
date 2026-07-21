from enum import StrEnum


class AdminTokenPurpose(StrEnum):
    TOTP_SETUP = "admin_totp_setup"
    LOGIN_2FA = "admin_login_2fa"


ADMIN_TOKEN_TTL_MINUTES = 5
TOTP_ISSUER_NAME = "Lucidex"
