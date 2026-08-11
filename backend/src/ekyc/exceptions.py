from src.exceptions import AppError


class InvalidNationalIdFormatError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            message="Invalid national ID format.",
            error_code="INVALID_NATIONAL_ID_FORMAT",
        )


class InvalidVnptAccessTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="Invalid VNPT eKYC access token.",
            error_code="INVALID_VNPT_ACCESS_TOKEN",
        )


class IdentityChangeNotAllowedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="Verified identity cannot be changed in this flow.",
            error_code="IDENTITY_CHANGE_NOT_ALLOWED",
        )


class IdentityAlreadyLinkedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="National ID is already linked to another Owner.",
            error_code="IDENTITY_ALREADY_LINKED",
        )


class EkycPersistenceFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            message="Verified identity could not be persisted.",
            error_code="EKYC_PERSISTENCE_FAILED",
        )


class EkycTimestampUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            message="Verified identity timestamp is unavailable.",
            error_code="EKYC_TIMESTAMP_UNAVAILABLE",
        )
