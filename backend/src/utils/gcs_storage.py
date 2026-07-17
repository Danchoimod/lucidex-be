import json
from functools import lru_cache
from pathlib import Path

from src.config import settings

try:
    from google.cloud import storage
    from google.oauth2 import credentials
except ImportError:  # pragma: no cover - exercised when dependency is absent
    storage = None
    credentials = None

LOCAL_UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "uploads"
LOCAL_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def connect_storage():
    if storage is None:
        raise RuntimeError("google-cloud-storage is not installed.")

    credentials_info = None
    if settings.GCS_CREDENTIALS_JSON:
        try:
            credentials_info = json.loads(settings.GCS_CREDENTIALS_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GCS_CREDENTIALS_JSON is not valid JSON.") from exc

    project_id = settings.GCS_PROJECT_ID or (
        credentials_info.get("project_id") if credentials_info else None
    )
    if not project_id:
        raise RuntimeError("GCS_PROJECT_ID is not configured.")

    if credentials_info and credentials is not None:
        try:
            google_credentials = credentials.Credentials(
                token=None,
                refresh_token=credentials_info.get("refresh_token"),
                id_token=None,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=credentials_info.get("client_id"),
                client_secret=credentials_info.get("client_secret"),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return storage.Client(project=project_id, credentials=google_credentials)
        except Exception:
            pass

    return storage.Client(project=project_id)


def upload_pdf(
    *,
    file_content: bytes | bytearray | Path,
    object_name: str,
) -> str:
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

    if (
        settings.FILE_STORAGE_BACKEND == "gcs"
        and settings.GCS_BUCKET_NAME
        and settings.GCS_PROJECT_ID
    ):
        try:
            bucket = connect_storage().bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(object_name)
            blob.upload_from_string(
                payload,
                content_type="application/pdf",
            )
            return blob.public_url
        except Exception as exc:
            raise RuntimeError(
                f"Unable to upload PDF to GCS: {exc}"
            ) from exc

    raise RuntimeError("GCS storage is not configured for PDF upload.")
