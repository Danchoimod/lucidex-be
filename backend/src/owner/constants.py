from enum import StrEnum


class OwnerStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    LOCKED_MIGRATED = "locked_migrated"
    SOFT_DELETED = "soft_deleted"


PASSWORD_MIN_LENGTH = 8
PASSWORD_REGEX_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z\d\s]).{8,}$"
