from typing import Any, Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class CsvUploadRow(Document):
    job_id: PydanticObjectId
    seq_no: int
    student_id: str
    raw_payload: dict[str, Any]
    validation_status: Literal[
        "valid", "invalid", "duplicate_pending", "resolved"
    ]
    error_reason: str | None = None
    resolution: Literal["overwrite", "skip"] | None = None
    processing_status: Literal["queued", "created", "failed"] = "queued"

    class Settings:
        name = "csv_upload_rows"
        indexes = [
            IndexModel([("job_id", ASCENDING), ("validation_status", ASCENDING)]),
            IndexModel([("job_id", ASCENDING), ("student_id", ASCENDING)]),
        ]
