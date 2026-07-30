from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import UploadFile

from src.credential.exceptions import NationalIdHashSecretNotConfiguredError
from src.issuer.exceptions import InvalidFileFormatError
from src.issuer.services import credential_import
from src.issuer.services.credential_import import CredentialImportService
from src.utils.hashing import hash_national_id

SECRET = "credential-import-test-secret"
RAW_NATIONAL_ID = "079-203-001-234"
EXPECTED_HASH = hash_national_id(RAW_NATIONAL_ID, SECRET)


class FakeFindQuery:
    def __init__(self, credentials: list[FakeCredential]) -> None:
        self._credentials = credentials

    async def to_list(self) -> list[FakeCredential]:
        return self._credentials


class FakeCredential:
    existing: list[FakeCredential] = []
    inserted: list[FakeCredential] = []

    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)
        self.saved = False

    @classmethod
    def find(cls, _query: dict[str, Any]) -> FakeFindQuery:
        return FakeFindQuery(cls.existing)

    async def insert(self) -> None:
        self.inserted.append(self)

    async def save(self) -> None:
        self.saved = True


def make_csv(national_id: str = RAW_NATIONAL_ID) -> UploadFile:
    content = (
        "student_id,full_name,dob,graduation_year,university_email,cccd\n"
        f"SV001,Nguyen Van A,2001-01-02,2024,a@example.edu.vn,{national_id}\n"
    ).encode()
    return UploadFile(filename="credentials.csv", file=BytesIO(content))


@pytest.fixture(autouse=True)
def patch_import_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeCredential.existing = []
    FakeCredential.inserted = []
    monkeypatch.setattr(credential_import, "Credential", FakeCredential)
    monkeypatch.setattr(
        credential_import,
        "upload_file",
        lambda **_kwargs: "issuer-imports/test/credentials.csv",
    )


def patch_hash_helper(monkeypatch: pytest.MonkeyPatch, received: list[str]) -> None:
    def hash_raw_national_id(value: str) -> str:
        received.append(value)
        return hash_national_id(value, SECRET)

    monkeypatch.setattr(
        credential_import,
        "hash_imported_national_id",
        hash_raw_national_id,
    )


@pytest.mark.asyncio
async def test_create_hashes_raw_national_id_before_persisting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[str] = []
    patch_hash_helper(monkeypatch, received)

    result = await CredentialImportService().import_credentials(
        file=make_csv(),
        overwrite_all_raw=False,
        organization=SimpleNamespace(id="org-1"),
        actor=SimpleNamespace(id="actor-1"),
    )

    assert received == [RAW_NATIONAL_ID]
    assert result.created_count == 1
    assert len(FakeCredential.inserted) == 1
    assert FakeCredential.inserted[0].national_id_hash == EXPECTED_HASH
    assert FakeCredential.inserted[0].national_id_hash != RAW_NATIONAL_ID


@pytest.mark.asyncio
async def test_overwrite_hashes_raw_national_id_before_persisting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[str] = []
    patch_hash_helper(monkeypatch, received)
    existing = FakeCredential(
        student_id="SV001",
        national_id_hash="old-hash",
    )
    FakeCredential.existing = [existing]

    result = await CredentialImportService().import_credentials(
        file=make_csv(),
        overwrite_all_raw=True,
        organization=SimpleNamespace(id="org-1"),
        actor=SimpleNamespace(id="actor-1"),
    )

    assert received == [RAW_NATIONAL_ID]
    assert result.updated_count == 1
    assert existing.saved is True
    assert existing.national_id_hash == EXPECTED_HASH
    assert existing.national_id_hash != RAW_NATIONAL_ID


@pytest.mark.asyncio
async def test_invalid_national_id_is_rejected_without_echoing_raw_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        credential_import,
        "hash_imported_national_id",
        lambda _value: (_ for _ in ()).throw(ValueError("invalid")),
    )

    with pytest.raises(InvalidFileFormatError) as exc_info:
        await CredentialImportService().import_credentials(
            file=make_csv("07920300123A"),
            overwrite_all_raw=False,
            organization=SimpleNamespace(id="org-1"),
            actor=SimpleNamespace(id="actor-1"),
        )

    assert exc_info.value.error_code == "INVALID_FILE_FORMAT"
    assert "07920300123A" not in exc_info.value.message


@pytest.mark.asyncio
async def test_missing_hash_secret_is_not_wrapped_as_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        credential_import,
        "hash_imported_national_id",
        lambda _value: (_ for _ in ()).throw(NationalIdHashSecretNotConfiguredError()),
    )

    with pytest.raises(NationalIdHashSecretNotConfiguredError):
        await CredentialImportService().import_credentials(
            file=make_csv(),
            overwrite_all_raw=False,
            organization=SimpleNamespace(id="org-1"),
            actor=SimpleNamespace(id="actor-1"),
        )
