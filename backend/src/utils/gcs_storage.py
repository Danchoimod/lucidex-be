from functools import lru_cache

from google.cloud import storage

from src.config import settings


@lru_cache(maxsize=1)
def connect_storage() -> storage.Client:
    if not settings.GCS_PROJECT_ID:
        raise RuntimeError("GCS_PROJECT_ID is not configured.")

    return storage.Client(project=settings.GCS_PROJECT_ID)


def upload_pdf(
    *,
    file_content: bytes,
    object_name: str,
) -> str:
    if not settings.GCS_BUCKET_NAME:
        raise RuntimeError("GCS_BUCKET_NAME is not configured.")

    if not file_content:
        raise ValueError("PDF file is empty.")

    bucket = connect_storage().bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)

    blob.upload_from_string(
        file_content,
        content_type="application/pdf",
    )

    return blob.public_url
