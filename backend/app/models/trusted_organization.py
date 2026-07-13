from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.models.base import utc_now


class TrustedOrganization(Document):
    owner_id: PydanticObjectId
    org_id: PydanticObjectId
    added_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "trusted_organizations"
        indexes = [
            IndexModel([("owner_id", ASCENDING), ("org_id", ASCENDING)], unique=True)
        ]
