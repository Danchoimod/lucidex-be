from typing import Literal

from beanie import Document
from pydantic import Field


class Role(Document):
    scope: Literal["issuer", "verifier", "admin"]
    name: str
    permissions: list[str] = Field(default_factory=list)

    class Settings:
        name = "roles"
