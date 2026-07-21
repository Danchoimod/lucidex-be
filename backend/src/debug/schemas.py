from pydantic import BaseModel, EmailStr


class DeleteUserDebugRequest(BaseModel):
    email: EmailStr


class DeleteUserDebugResponse(BaseModel):
    deleted_owners: int
    deleted_institution_accounts: int
    deleted_organizations: int
    deleted_invites: int
    deleted_sessions: int
    deleted_otps: int
