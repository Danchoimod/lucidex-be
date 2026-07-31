from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OwnerEkycStatus = Literal["not_verified", "verified"]


class VerifyOwnerEkycRequest(BaseModel):
    national_id: str = Field(
        min_length=1,
        description=(
            "Vietnamese national ID. Whitespace and hyphens are normalized; "
            "the normalized value must contain exactly 12 ASCII digits."
        ),
        examples=["079203001234"],
    )
    access_token: str = Field(
        min_length=1,
        description="VNPT eKYC access token configured by the platform.",
        examples=["vnpt-token"],
    )

    model_config = ConfigDict(extra="forbid")


class VerifyOwnerEkycData(BaseModel):
    identity_matched: bool
    ekyc_status: Literal["verified"]
    verified_at: datetime


class OwnerEkycStatusData(BaseModel):
    status: OwnerEkycStatus
    verification_id: str | None
    provider: str | None
    verified_at: datetime | None
