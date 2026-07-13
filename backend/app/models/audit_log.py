from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel

from app.models.base import utc_now


class AuditLog(Document):
    actor_type: Literal["issuer", "owner", "verifier", "admin"]
    actor_id: PydanticObjectId
    action_type: str
    detail: str
    timestamp: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "audit_logs"
        indexes = [
            IndexModel([("detail", TEXT)], name="text_audit_detail"),
            IndexModel(
                [
                    ("actor_type", ASCENDING),
                    ("action_type", ASCENDING),
                    ("timestamp", DESCENDING),
                ]
            ),
        ]
