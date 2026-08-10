from src.exceptions import AppError


class OwnerAccessRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="Owner access is required.",
            error_code="OWNER_ACCESS_REQUIRED",
        )


class OwnerInactiveError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="Active owner account is required.",
            error_code="OWNER_INACTIVE",
        )


class InvalidOwnerAccountError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            message="Invalid owner account.",
            error_code="INVALID_OWNER_ACCOUNT",
        )


class NationalIdHashSecretNotConfiguredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            message="National ID hash secret is not configured.",
            error_code="NATIONAL_ID_HASH_SECRET_NOT_CONFIGURED",
        )


class CredentialNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            message="Credential not found.",
            error_code="CREDENTIAL_NOT_FOUND",
        )


class EkycVerificationRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="eKYC verification is required.",
            error_code="EKYC_NOT_VERIFIED",
        )


class CredentialAlreadyClaimedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="Credential was already claimed.",
            error_code="CREDENTIAL_ALREADY_CLAIMED",
        )


class CredentialIdentityMismatchError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="Credential does not belong to your verified identity.",
            error_code="CREDENTIAL_NOT_MATCHED",
        )


class CredentialNotClaimableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="Credential is not claimable.",
            error_code="MATCH_NOT_CLAIMABLE",
        )


class CredentialNotClaimedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Credential must be claimed before creating a verified link.",
            error_code="CREDENTIAL_NOT_CLAIMED",
        )


class InvalidExpirationError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Expiration date must be in the future.",
            error_code="INVALID_EXPIRATION",
        )


class InvalidAccessCountError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Max access count must be at least 1.",
            error_code="INVALID_ACCESS_COUNT",
        )


class VerifiedLinkNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            message="Verification link not found.",
            error_code="VERIFIED_LINK_NOT_FOUND",
        )


class LinkExpiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Verification link has expired.",
            error_code="LINK_EXPIRED",
        )


class LinkExhaustedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Verification link max access count has been exhausted.",
            error_code="LINK_EXHAUSTED",
        )


class LinkAlreadyRevokedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Verification link is already revoked.",
            error_code="LINK_ALREADY_REVOKED",
        )

