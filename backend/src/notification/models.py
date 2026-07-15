from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.models import utc_now


class Notification(Document):
    owner_id: PydanticObjectId
    type: Literal[
        "claim_submitted",
        "claim_review",
        "claim_approved",
        "claim_rejected",
        "link_viewed",
        "access_denied",
        "access_request_pending",
    ]
    message: str
    related_entity_id: PydanticObjectId | None = None
    related_entity_type: str | None = None
    is_read: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "notifications"
        indexes = [
            IndexModel(
                [("owner_id", ASCENDING), ("is_read", ASCENDING), ("created_at", DESCENDING)]
            )
        ]
