import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.auth.credentials import Credentials
from google.auth.exceptions import GoogleAuthError
from google.cloud import storage
from google.oauth2 import credentials as user_credentials
from google.oauth2 import service_account

from src.config import settings

GCS_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _load_credentials_info() -> dict[str, Any] | None:
    if not settings.GCS_CREDENTIALS_JSON:
        return None

    try:
        credentials_info = json.loads(settings.GCS_CREDENTIALS_JSON)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GCS_CREDENTIALS_JSON is not valid JSON.") from exc
    if not isinstance(credentials_info, dict):
        raise RuntimeError("GCS_CREDENTIALS_JSON must contain a JSON object.")
    return credentials_info


def _create_credentials(info: dict[str, Any] | None) -> Credentials | None:
    if not info:
        return None

    try:
        if info.get("type") == "service_account":
            return service_account.Credentials.from_service_account_info(
                info, scopes=GCS_SCOPES
            )
        return user_credentials.Credentials.from_authorized_user_info(
            info, scopes=GCS_SCOPES
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Invalid GCS credentials JSON.") from exc


def _get_bucket_name() -> str:
    if (
        settings.FILE_STORAGE_BACKEND != "gcs"
        or not settings.GCS_BUCKET_NAME
        or not settings.GCS_PROJECT_ID
    ):
        raise RuntimeError("GCS storage is not configured for PDF upload.")
    return settings.GCS_BUCKET_NAME


def _read_payload(file_content: bytes | bytearray | Path) -> bytes:
    if isinstance(file_content, Path):
        if not file_content.exists():
            raise FileNotFoundError(f"File not found: {file_content}")
        payload = file_content.read_bytes()
    elif isinstance(file_content, (bytes, bytearray)):
        payload = bytes(file_content)
    else:
        raise TypeError("file_content must be bytes, bytearray, or a Path")

    if not payload:
        raise ValueError("PDF file is empty.")
    return payload


@lru_cache(maxsize=1)
def connect_storage() -> storage.Client:
    info = _load_credentials_info()
    project_id = settings.GCS_PROJECT_ID or (info or {}).get("project_id")
    if not project_id:
        raise RuntimeError("GCS_PROJECT_ID is not configured.")

    return storage.Client(
        project=project_id,
        credentials=_create_credentials(info),
    )


def upload_pdf(
    *,
    file_content: bytes | bytearray | Path,
    object_name: str,
) -> str:
    payload = _read_payload(file_content)
    bucket_name = _get_bucket_name()

    try:
        bucket = connect_storage().bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(payload, content_type="application/pdf")
    except (GoogleAPIError, GoogleAuthError) as exc:
        raise RuntimeError(f"Unable to upload PDF to GCS: {exc}") from exc

    return blob.public_url
