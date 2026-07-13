from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class EkycCaptureSession(Document):
    owner_id: PydanticObjectId
    claim_id: PydanticObjectId
    token: str
    status: Literal[
        "pending", "submitted", "processing", "completed", "expired"
    ] = "pending"
    expires_at: datetime
    outcome: Literal[
        "auto_approved", "low_confidence", "unreadable_image", "liveness_failed"
    ] | None = None

    class Settings:
        name = "ekyc_capture_sessions"
        indexes = [
            IndexModel([("token", ASCENDING)], unique=True),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ]
