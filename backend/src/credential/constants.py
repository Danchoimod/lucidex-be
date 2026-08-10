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


DENIAL_MESSAGES = {
    "INVALID_VERIFICATION_CODE": "Invalid code. Please check and try again.",
    "LINK_EXPIRED": "This link has expired.",
    "LINK_REVOKED": "Access revoked.",
    "LINK_EXHAUSTED": "This link is no longer available.",
    "UNAUTHORIZED_VERIFIER": "This organization is not authorized to view this credential.",
    "CREDENTIAL_REVOKED": "The credential associated with this link has been revoked.",
}

