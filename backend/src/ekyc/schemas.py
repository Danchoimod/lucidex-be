from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VerifyOwnerEkycRequest(BaseModel):
    national_id: str = Field(
        min_length=1,
        description=(
            "Vietnamese national ID. Whitespace and hyphens are normalized; "
            "the normalized value must contain exactly 12 ASCII digits."
        ),
        examples=["079203001234"],
    )

    model_config = ConfigDict(extra="forbid")


class VerifyOwnerEkycData(BaseModel):
    identity_matched: bool
    ekyc_status: Literal["verified"]
    verified_at: datetime
