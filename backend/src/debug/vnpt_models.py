from beanie import Document
from pydantic import BaseModel, Field


class VnptEkycConfig(Document):
    config_key: str = Field(default="global_vnpt_config", unique=True)
    access_token: str | None = None
    token_id: str | None = None
    token_key: str | None = None
    public_key_ca: str | None = None

    class Settings:
        name = "vnpt_ekyc_configs"


class VnptEkycConfigRequest(BaseModel):
    access_token: str | None = None
    token_id: str | None = None
    token_key: str | None = None
    public_key_ca: str | None = None


class VnptEkycConfigResponse(BaseModel):
    access_token: str | None = None
    token_id: str | None = None
    token_key: str | None = None
    public_key_ca: str | None = None

