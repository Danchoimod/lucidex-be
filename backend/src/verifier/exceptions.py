from src.exceptions import AppError


class InvalidCsvFileError(AppError):
    """Raised when uploaded file cannot be parsed as a single-column CSV or is empty."""

    def __init__(self, message: str = "Invalid or empty CSV file.") -> None:
        super().__init__(
            status_code=400,
            message=message,
            error_code="INVALID_CSV_FILE",
        )


class BulkVerifyRowLimitExceededError(AppError):
    """Raised when CSV contains more than the allowed maximum number of rows."""

    def __init__(self, limit: int = 500) -> None:
        super().__init__(
            status_code=422,
            message=f"Row limit exceeded. Max {limit} codes per request.",
            error_code="BULK_VERIFY_ROW_LIMIT_EXCEEDED",
        )
