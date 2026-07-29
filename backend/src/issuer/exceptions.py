"""Exceptions for the issuer module."""

from src.exceptions import AppError


class FileRequiredError(AppError):
    """Raised when no file is uploaded in the request."""

    def __init__(self, message: str = "No file uploaded.") -> None:
        super().__init__(status_code=400, message=message, error_code="FILE_REQUIRED")


class InvalidFileFormatError(AppError):
    """Raised when uploaded file is not a valid CSV, has wrong encoding or invalid header template."""

    def __init__(
        self,
        message: str = "Invalid CSV file format, encoding, or header template.",
    ) -> None:
        super().__init__(
            status_code=400, message=message, error_code="INVALID_FILE_FORMAT"
        )


class CsvNoRecordsError(AppError):
    """Raised when the uploaded CSV contains no data rows."""

    def __init__(self, message: str = "CSV file contains no data rows.") -> None:
        super().__init__(status_code=400, message=message, error_code="CSV_NO_RECORDS")


class InvalidOverwriteValueError(AppError):
    """Raised when overwrite_all parameter is invalid or missing."""

    def __init__(
        self, message: str = "overwrite_all parameter must be true or false."
    ) -> None:
        super().__init__(
            status_code=400, message=message, error_code="INVALID_OVERWRITE_VALUE"
        )


class ItemsLimitExceededError(AppError):
    """Raised when the number of CSV rows exceeds the maximum allowed limit."""

    def __init__(
        self, message: str = "Number of rows exceeds the maximum allowed limit."
    ) -> None:
        super().__init__(
            status_code=400, message=message, error_code="ITEMS_LIMIT_EXCEEDED"
        )


class IssuerForbiddenError(AppError):
    """Raised when the authenticated actor does not have Issuer permissions."""

    def __init__(
        self, message: str = "Actor does not have Issuer organization permission."
    ) -> None:
        super().__init__(status_code=403, message=message, error_code="FORBIDDEN")


class CredentialImportFailedError(AppError):
    """Raised when database operations fail during credential import."""

    def __init__(
        self, message: str = "Failed to insert or update credentials in database."
    ) -> None:
        super().__init__(
            status_code=500, message=message, error_code="CREDENTIAL_IMPORT_FAILED"
        )


class CredentialFileUploadFailedError(AppError):
    """Raised when uploading CSV file to storage fails."""

    def __init__(self, message: str = "Failed to upload CSV file to storage.") -> None:
        super().__init__(
            status_code=502, message=message, error_code="CREDENTIAL_FILE_UPLOAD_FAILED"
        )
