from typing import Literal

from beanie import Document, PydanticObjectId


class CsvUploadJob(Document):
    org_id: PydanticObjectId
    filename: str
    total_rows: int = 0
    valid_count: int = 0
    error_count: int = 0
    created_count: int = 0
    status: Literal[
        "validating",
        "awaiting_confirmation",
        "processing",
        "completed",
        "failed",
    ] = "validating"
    overwrite_all: bool = False

    class Settings:
        name = "csv_upload_jobs"
