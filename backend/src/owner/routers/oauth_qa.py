import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from src.config import settings

QA_ENVIRONMENTS = {"local", "development", "test"}
QA_PAGE_PATH = Path(__file__).resolve().parents[1] / "templates" / "google_oauth_qa.html"

router = APIRouter(prefix="/owner/auth", tags=["Debug / Testing"])


def _render_qa_page(client_id: str) -> str:
    template = QA_PAGE_PATH.read_text(encoding="utf-8")
    client_id_json = json.dumps(client_id).replace("<", "\\u003c")
    return template.replace("__GOOGLE_CLIENT_ID_JSON__", client_id_json)


@router.get(
    "/google/test",
    response_class=HTMLResponse,
    summary="Open the Owner Google OAuth QA test page",
    description=(
        "[Open Google OAuth QA page](/api/v1/owner/auth/google/test) in a "
        "browser tab. This development-only page obtains a temporary Google "
        "ID token for manual testing of `POST /api/v1/owner/auth/google`. It "
        "returns 404 outside local, development, and test environments."
    ),
    include_in_schema=settings.ENV in QA_ENVIRONMENTS,
)
async def google_oauth_qa_test_page() -> HTMLResponse:
    if settings.ENV not in QA_ENVIRONMENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )
    return HTMLResponse(_render_qa_page(settings.GOOGLE_CLIENT_ID))
