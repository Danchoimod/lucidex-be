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
            message="Credential does not match the verified identity.",
            error_code="CREDENTIAL_NOT_MATCHED",
        )


class CredentialNotClaimableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="Credential is not claimable.",
            error_code="MATCH_NOT_CLAIMABLE",
        )
