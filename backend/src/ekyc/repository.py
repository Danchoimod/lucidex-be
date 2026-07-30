from dataclasses import dataclass
from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.ekyc.models import OwnerEkycIdentity


@dataclass(frozen=True)
class EkycIdentityState:
    owner_id: PydanticObjectId
    national_id_hash: str
    status: str
    verified_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "EkycIdentityState":
        return cls(
            owner_id=document["owner_id"],
            national_id_hash=document["national_id_hash"],
            status=document["status"],
            verified_at=document["verified_at"],
        )


class EkycRepository:
    async def bind_verified_identity(
        self,
        *,
        owner_id: PydanticObjectId,
        national_id_hash: str,
        verified_at: datetime,
    ) -> EkycIdentityState | None:
        collection = OwnerEkycIdentity.get_motor_collection()
        try:
            document = await collection.find_one_and_update(
                {
                    "owner_id": owner_id,
                    "$or": [
                        {"national_id_hash": national_id_hash},
                        {"national_id_hash": None},
                        {"national_id_hash": {"$exists": False}},
                    ],
                },
                {
                    "$set": {
                        "national_id_hash": national_id_hash,
                        "status": "verified",
                    },
                    "$setOnInsert": {
                        "owner_id": owner_id,
                        "verified_at": verified_at,
                    },
                },
                projection={
                    "owner_id": 1,
                    "national_id_hash": 1,
                    "status": 1,
                    "verified_at": 1,
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            return None
        if document is None:
            return None
        return EkycIdentityState.from_document(document)

    async def get_verified_identity(
        self,
        owner_id: PydanticObjectId,
    ) -> EkycIdentityState | None:
        document = await OwnerEkycIdentity.get_motor_collection().find_one(
            {
                "owner_id": owner_id,
                "status": "verified",
            },
            {
                "owner_id": 1,
                "national_id_hash": 1,
                "status": 1,
                "verified_at": 1,
            },
        )
        if document is None:
            return None
        return EkycIdentityState.from_document(document)

    async def get_by_national_id_hash(
        self,
        national_id_hash: str,
    ) -> EkycIdentityState | None:
        document = await OwnerEkycIdentity.get_motor_collection().find_one(
            {"national_id_hash": national_id_hash},
            {
                "owner_id": 1,
                "national_id_hash": 1,
                "status": 1,
                "verified_at": 1,
            },
        )
        if document is None:
            return None
        return EkycIdentityState.from_document(document)


ekyc_repository = EkycRepository()
