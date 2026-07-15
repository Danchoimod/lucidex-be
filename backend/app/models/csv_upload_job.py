from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.models.base import utc_now


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
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "csv_upload_jobs"
        indexes = [
            IndexModel(
                [("org_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
                name="ix_csv_upload_job_resume",
            )
        ]
