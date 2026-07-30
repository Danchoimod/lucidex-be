from dataclasses import dataclass
from datetime import datetime
from re import escape
from typing import Any

from beanie import PydanticObjectId
from pymongo import ReturnDocument

from src.credential.constants import (
    CredentialClaimMethod,
    CredentialStatus,
    OwnerCredentialStatus,
)
from src.credential.models import Credential


@dataclass(frozen=True)
class OwnerCredentialListResult:
    items: list[dict[str, Any]]
    total_credentials: int
    total_claimed: int
    total_unclaimed: int


def build_owner_credential_scope(
    *,
    owner_id: PydanticObjectId,
    verified_national_id_hash: str | None,
) -> dict[str, Any]:
    claimed_scope = {
        "owner_id": owner_id,
        "status": CredentialStatus.CLAIMED.value,
    }
    if not verified_national_id_hash:
        return {
            "deleted_at": None,
            **claimed_scope,
        }
    return {
        "deleted_at": None,
        "$or": [
            claimed_scope,
            {
                "owner_id": None,
                "status": CredentialStatus.UNCLAIMED.value,
                "national_id_hash": verified_national_id_hash,
            },
        ],
    }


class CredentialRepository:
    async def list_for_owner(
        self,
        *,
        owner_id: PydanticObjectId,
        verified_national_id_hash: str | None,
        page: int,
        limit: int,
        student_id: str | None,
        graduation_year: int | None,
        status: OwnerCredentialStatus | None,
        search: str | None,
        sort_field: str,
        sort_direction: int,
    ) -> OwnerCredentialListResult:
        scope = build_owner_credential_scope(
            owner_id=owner_id,
            verified_national_id_hash=verified_national_id_hash,
        )
        filters: list[dict[str, Any]] = []
        if student_id:
            filters.append({"student_id": student_id})
        if graduation_year is not None:
            filters.append({"graduation_year": graduation_year})
        if status is not None:
            filters.append({"status": status.value})
        if search:
            safe_pattern = escape(search)
            filters.append(
                {
                    "$or": [
                        {"student_id": {"$regex": safe_pattern, "$options": "i"}},
                        {"full_name": {"$regex": safe_pattern, "$options": "i"}},
                        {"major": {"$regex": safe_pattern, "$options": "i"}},
                        {
                            "classification": {
                                "$regex": safe_pattern,
                                "$options": "i",
                            }
                        },
                    ]
                }
            )

        query = {"$and": [scope, *filters]} if filters else scope
        pipeline = [
            {"$match": query},
            {
                "$facet": {
                    "items": [
                        {
                            "$sort": {
                                sort_field: sort_direction,
                                "_id": sort_direction,
                            }
                        },
                        {"$skip": (page - 1) * limit},
                        {"$limit": limit},
                        {
                            "$project": {
                                "_id": 1,
                                "student_id": 1,
                                "full_name": 1,
                                "graduation_year": 1,
                                "status": 1,
                                "owner_id": 1,
                                "claimed_at": 1,
                            }
                        },
                    ],
                    "summary": [
                        {
                            "$group": {
                                "_id": None,
                                "total_credentials": {"$sum": 1},
                                "total_claimed": {
                                    "$sum": {
                                        "$cond": [
                                            {
                                                "$eq": [
                                                    "$status",
                                                    CredentialStatus.CLAIMED.value,
                                                ]
                                            },
                                            1,
                                            0,
                                        ]
                                    }
                                },
                                "total_unclaimed": {
                                    "$sum": {
                                        "$cond": [
                                            {
                                                "$eq": [
                                                    "$status",
                                                    CredentialStatus.UNCLAIMED.value,
                                                ]
                                            },
                                            1,
                                            0,
                                        ]
                                    }
                                },
                            }
                        }
                    ],
                }
            },
        ]
        results = (
            await Credential.get_motor_collection()
            .aggregate(pipeline)
            .to_list(length=1)
        )
        facet = results[0] if results else {"items": [], "summary": []}
        summary = facet["summary"][0] if facet["summary"] else {}
        return OwnerCredentialListResult(
            items=facet["items"],
            total_credentials=summary.get("total_credentials", 0),
            total_claimed=summary.get("total_claimed", 0),
            total_unclaimed=summary.get("total_unclaimed", 0),
        )

    async def get_for_owner(
        self,
        *,
        credential_id: PydanticObjectId,
        owner_id: PydanticObjectId,
        verified_national_id_hash: str | None,
    ) -> dict[str, Any] | None:
        scope = build_owner_credential_scope(
            owner_id=owner_id,
            verified_national_id_hash=verified_national_id_hash,
        )
        pipeline = [
            {"$match": {"$and": [{"_id": credential_id}, scope]}},
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "issuer_org_id",
                    "foreignField": "_id",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 1,
                                "name": 1,
                                "address": 1,
                                "contact_email": 1,
                                "contact_phone": 1,
                            }
                        }
                    ],
                    "as": "issuer",
                }
            },
            {
                "$set": {
                    "issuer": {"$arrayElemAt": ["$issuer", 0]},
                }
            },
            {
                "$project": {
                    "national_id_hash": 0,
                    "owner_id": 0,
                    "unclaimed_reason_code": 0,
                    "created_at": 0,
                }
            },
        ]
        results = (
            await Credential.get_motor_collection()
            .aggregate(pipeline)
            .to_list(length=1)
        )
        return results[0] if results else None

    async def claim_for_owner(
        self,
        *,
        credential_id: PydanticObjectId,
        owner_id: PydanticObjectId,
        verified_national_id_hash: str,
        claimed_at: datetime,
    ) -> dict[str, Any] | None:
        return await Credential.get_motor_collection().find_one_and_update(
            {
                "_id": credential_id,
                "deleted_at": None,
                "owner_id": None,
                "status": CredentialStatus.UNCLAIMED.value,
                "national_id_hash": verified_national_id_hash,
            },
            {
                "$set": {
                    "owner_id": owner_id,
                    "status": CredentialStatus.CLAIMED.value,
                    "claimed_at": claimed_at,
                    "claim_method": CredentialClaimMethod.MANUAL.value,
                }
            },
            projection={
                "_id": 1,
                "status": 1,
                "claim_method": 1,
                "claimed_at": 1,
            },
            return_document=ReturnDocument.AFTER,
        )

    async def get_claim_state(
        self,
        credential_id: PydanticObjectId,
    ) -> dict[str, Any] | None:
        return await Credential.get_motor_collection().find_one(
            {
                "_id": credential_id,
                "deleted_at": None,
            },
            {
                "_id": 1,
                "owner_id": 1,
                "status": 1,
                "national_id_hash": 1,
                "claim_method": 1,
                "claimed_at": 1,
            },
        )

    async def has_unclaimed_national_id_hash(
        self,
        national_id_hash: str,
    ) -> bool:
        credential = await Credential.get_motor_collection().find_one(
            {
                "deleted_at": None,
                "status": CredentialStatus.UNCLAIMED.value,
                "owner_id": None,
                "national_id_hash": national_id_hash,
            },
            {"_id": 1},
        )
        return credential is not None


credential_repository = CredentialRepository()
