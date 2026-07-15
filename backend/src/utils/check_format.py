import re

# General email syntax used before applying provider-specific rules.
mail_pattern = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?"
    r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z]{2,})+$"
)

# vietnamphone begin = 0..., not +84
phone_pattern = re.compile(
    r"^0(?:3|5|7|8|9)\d{8}$"
)

# tax 10 num: 000000000
# or 10 num - 3 num: 0000000000-000
tax_code_pattern = re.compile(
    r"^\d{10}(?:-\d{3})?$"
)


def normalize_email(email: str) -> str:
    """Trim and lowercase an email address before validation/storage."""
    return email.strip().lower()


def validate_email_format(email: str) -> bool:
    """Return True when the email is a syntactically valid email address."""
    return bool(mail_pattern.fullmatch(normalize_email(email)))


def validate_gmail_format(email: str) -> bool:
    """Return True when the address is valid and belongs to gmail.com."""
    normalized_email = normalize_email(email)
    return (
        validate_email_format(normalized_email)
        and normalized_email.endswith("@gmail.com")
    )


def normalize_phone(phone: str) -> str:
    """Normalize a Vietnamese phone number by removing visual separators."""
    return (
        phone.strip()
        .replace(" ", "")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
    )


def validate_phone_format(phone: str) -> bool:
    """Return True for common Vietnamese mobile phone formats."""
    return bool(phone_pattern.fullmatch(normalize_phone(phone)))


def normalize_tax_code(tax_code: str) -> str:
    """Normalize a Vietnamese tax code by trimming whitespace."""
    return tax_code.strip()


def validate_tax_code_format(tax_code: str) -> bool:
    """Return True for 10-digit or 10-digit-branch Vietnamese tax codes."""
    return bool(tax_code_pattern.fullmatch(normalize_tax_code(tax_code)))
