from enum import StrEnum

DEFAULT_DEGREE_TYPE = "Bằng tốt nghiệp đại học"


class CredentialStatus(StrEnum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    REVOKED = "revoked"


class OwnerCredentialStatus(StrEnum):
    CLAIMED = "claimed"
    UNCLAIMED = "unclaimed"


class CredentialClaimMethod(StrEnum):
    UNIVERSITY_EMAIL = "university_email"
    NATIONAL_ID = "national_id"
    MANUAL = "manual"


DEFAULT_PAGE = 1
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
DEFAULT_CREDENTIAL_SORT = "_id:desc"
OWNER_CREDENTIAL_SORT_FIELDS = frozenset(
    {
        "_id",
        "claimed_at",
        "full_name",
        "graduation_year",
        "student_id",
    }
)
