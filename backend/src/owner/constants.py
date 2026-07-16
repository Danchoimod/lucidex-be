from enum import Enum


class OwnerStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    LOCKED_MIGRATED = "locked_migrated"
    SOFT_DELETED = "soft_deleted"


class ConsentType(str, Enum):
    ONE_TIME = "one_time"
    PER_REQUEST = "per_request"
    ORG_LEVEL = "org_level"
    TIME_BOUND = "time_bound"


class ConsentDuration(str, Enum):
    D_24H = "24h"
    D_7D = "7d"
    D_30D = "30d"
    PERMANENT = "permanent"


PASSWORD_MIN_LENGTH = 8
PASSWORD_REGEX_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z\d\s]).{8,}$"
