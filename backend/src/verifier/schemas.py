from pydantic import BaseModel, Field


class BulkVerifyRowResult(BaseModel):
    row_number: int = Field(description="1-indexed row position in the uploaded CSV.")
    code: str = Field(description="Plaintext verification code.")
    status: str = Field(description="Status outcome: active, expired, revoked, or not_found.")
    is_restricted: bool = Field(
        default=False,
        description="True if active but restricted to specific verifier organizations.",
    )
    credential_id: str | None = Field(
        default=None,
        description="ObjectId of credential if active and non-restricted.",
    )
    owner_name: str | None = Field(
        default=None,
        description="Full name of credential owner if active and non-restricted.",
    )
    credential_type: str | None = Field(
        default=None,
        description="Degree type if active and non-restricted.",
    )


class BulkVerifySummary(BaseModel):
    active: int = Field(default=0, description="Count of active rows.")
    expired: int = Field(default=0, description="Count of expired/exhausted rows.")
    revoked: int = Field(default=0, description="Count of revoked rows.")
    not_found: int = Field(default=0, description="Count of unrecognized codes.")


class BulkVerifyResponse(BaseModel):
    batch_id: str = Field(description="Unique UUID4 identifier for this bulk verification batch.")
    total: int = Field(description="Total non-blank rows processed.")
    summary: BulkVerifySummary = Field(description="Outcome distribution summary.")
    results: list[BulkVerifyRowResult] = Field(
        default_factory=list,
        description="Per-row verification outcomes in input order.",
    )
