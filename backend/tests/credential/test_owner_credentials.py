import asyncio
from datetime import UTC, date, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from src.auth.dependencies import require_current_actor
from src.credential.constants import OwnerCredentialStatus
from src.credential.dependencies import require_current_active_owner
from src.credential.models import Credential
from src.credential.repository import (
    CredentialRepository,
    OwnerCredentialListResult,
    build_owner_credential_scope,
)
from src.credential.schemas import (
    ClaimCredentialData,
    ClaimedCredentialData,
    OwnerCredentialDetail,
    OwnerCredentialIssuerDetail,
    OwnerCredentialListData,
    OwnerCredentialListItem,
    OwnerCredentialListQuery,
    OwnerCredentialPagination,
    OwnerCredentialSummary,
)
from src.credential.services import (
    OwnerCredentialClaimService,
    OwnerCredentialDetailService,
    OwnerCredentialListService,
    owner_credential_claim_service,
    owner_credential_detail_service,
    owner_credential_list_service,
)
from src.ekyc.repository import EkycIdentityState, EkycRepository
from src.exceptions import AppError
from src.main import app
from src.owner.constants import OwnerStatus
from src.owner.models import Owner

OWNER_ID = PydanticObjectId("507f1f77bcf86cd799439011")
OTHER_OWNER_ID = PydanticObjectId("507f1f77bcf86cd799439012")
CREDENTIAL_ID = PydanticObjectId("507f1f77bcf86cd799439013")
ISSUER_ID = PydanticObjectId("507f1f77bcf86cd799439014")
VERIFIED_HASH = "a" * 64
NOW = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)


def make_owner(
    *,
    owner_id: PydanticObjectId = OWNER_ID,
    status: OwnerStatus = OwnerStatus.ACTIVE,
    deleted_at: datetime | None = None,
) -> Owner:
    return Owner.model_construct(
        id=owner_id,
        email="owner@example.com",
        status=status,
        deleted_at=deleted_at,
    )


def detail_record(**overrides: Any) -> dict[str, Any]:
    record = {
        "_id": CREDENTIAL_ID,
        "issuer_org_id": ISSUER_ID,
        "issuer": {
            "_id": ISSUER_ID,
            "name": "Lucidex University",
            "address": "1 Education Street",
            "contact_email": "contact@lucidex.edu.vn",
            "contact_phone": "02812345678",
        },
        "student_id": "B2203243",
        "full_name": "Nguyen Van A",
        "dob": date(2001, 1, 1),
        "major": "Computer Science",
        "major_vi": "Khoa học máy tính",
        "major_en": "Computer Science",
        "degree_type": "Bachelor of Engineering",
        "graduation_year": 2023,
        "classification": "Good",
        "graduation_classification_vi": "Giỏi",
        "graduation_classification_en": "Good",
        "university_email": "student@example.edu",
        "phone": "0912345678",
        "status": "claimed",
        "claim_method": "manual",
        "claimed_at": NOW,
        "created_at": NOW,
    }
    record.update(overrides)
    return record


class FakeRepository:
    def __init__(self) -> None:
        self.list_result = OwnerCredentialListResult([], 0, 0, 0)
        self.detail: dict[str, Any] | None = None
        self.claimed: dict[str, Any] | None = None
        self.claim_state: dict[str, Any] | None = None
        self.list_arguments: dict[str, Any] | None = None
        self.detail_arguments: dict[str, Any] | None = None
        self.claim_arguments: dict[str, Any] | None = None

    async def list_for_owner(self, **kwargs: Any) -> OwnerCredentialListResult:
        self.list_arguments = kwargs
        return self.list_result

    async def get_for_owner(self, **kwargs: Any) -> dict[str, Any] | None:
        self.detail_arguments = kwargs
        return self.detail

    async def claim_for_owner(self, **kwargs: Any) -> dict[str, Any] | None:
        self.claim_arguments = kwargs
        return self.claimed

    async def get_claim_state(
        self,
        credential_id: PydanticObjectId,
    ) -> dict[str, Any] | None:
        assert credential_id == CREDENTIAL_ID
        return self.claim_state


class FakeIdentityRepository:
    def __init__(self, national_id_hash: str | None = VERIFIED_HASH) -> None:
        self.national_id_hash = national_id_hash
        self.owner_ids: list[PydanticObjectId] = []

    async def get_verified_identity(
        self,
        owner_id: PydanticObjectId,
    ) -> EkycIdentityState | None:
        self.owner_ids.append(owner_id)
        if self.national_id_hash is None:
            return None
        return EkycIdentityState(
            owner_id=owner_id,
            national_id_hash=self.national_id_hash,
            status="verified",
            verified_at=NOW,
        )


def make_list_service(
    repository: FakeRepository,
    identity_hash: str | None = VERIFIED_HASH,
) -> OwnerCredentialListService:
    return OwnerCredentialListService(
        cast(CredentialRepository, repository),
        cast(EkycRepository, FakeIdentityRepository(identity_hash)),
    )


def make_detail_service(
    repository: FakeRepository,
    identity_hash: str | None = VERIFIED_HASH,
) -> OwnerCredentialDetailService:
    return OwnerCredentialDetailService(
        cast(CredentialRepository, repository),
        cast(EkycRepository, FakeIdentityRepository(identity_hash)),
    )


def make_claim_service(
    repository: FakeRepository,
    identity_hash: str | None = VERIFIED_HASH,
) -> OwnerCredentialClaimService:
    return OwnerCredentialClaimService(
        cast(CredentialRepository, repository),
        cast(EkycRepository, FakeIdentityRepository(identity_hash)),
    )


def test_owner_security_scope_includes_only_authorized_groups() -> None:
    without_hash = build_owner_credential_scope(
        owner_id=OWNER_ID,
        verified_national_id_hash=None,
    )
    with_hash = build_owner_credential_scope(
        owner_id=OWNER_ID,
        verified_national_id_hash=VERIFIED_HASH,
    )

    assert without_hash == {
        "deleted_at": None,
        "owner_id": OWNER_ID,
        "status": "claimed",
    }
    assert with_hash == {
        "deleted_at": None,
        "$or": [
            {"owner_id": OWNER_ID, "status": "claimed"},
            {
                "owner_id": None,
                "status": "unclaimed",
                "national_id_hash": VERIFIED_HASH,
            },
        ],
    }


@pytest.mark.asyncio
async def test_list_maps_claimed_and_matched_unclaimed_without_hash() -> None:
    repository = FakeRepository()
    repository.list_result = OwnerCredentialListResult(
        items=[
            {
                "_id": CREDENTIAL_ID,
                "student_id": "B2203243",
                "full_name": "Nguyen Van A",
                "graduation_year": 2023,
                "status": "claimed",
                "owner_id": OWNER_ID,
                "claimed_at": NOW,
                "created_at": NOW,
            },
            {
                "_id": PydanticObjectId("507f1f77bcf86cd799439015"),
                "student_id": "B2203244",
                "full_name": "Nguyen Van B",
                "graduation_year": 2024,
                "status": "unclaimed",
                "owner_id": None,
                "claimed_at": None,
                "created_at": NOW,
            },
        ],
        total_credentials=4,
        total_claimed=1,
        total_unclaimed=3,
    )
    service = make_list_service(repository)

    data = await service.list_credentials(
        owner=make_owner(),
        query=OwnerCredentialListQuery(page=1, limit=2),
    )

    assert [item.can_claim for item in data.items] == [False, True]
    assert data.summary.model_dump() == {
        "total_credentials": 4,
        "total_claimed": 1,
        "total_unclaimed": 3,
    }
    assert data.pagination.total_items == 4
    assert data.pagination.total_pages == 2
    assert "national_id_hash" not in data.model_dump_json()
    assert "created_at" not in data.model_dump_json()


@pytest.mark.asyncio
async def test_unverified_owner_list_still_queries_claimed_credentials() -> None:
    repository = FakeRepository()
    service = make_list_service(repository, identity_hash=None)

    await service.list_credentials(
        owner=make_owner(),
        query=OwnerCredentialListQuery(),
    )

    assert repository.list_arguments is not None
    assert repository.list_arguments["verified_national_id_hash"] is None
    assert repository.list_arguments["sort_field"] == "_id"


@pytest.mark.asyncio
async def test_list_passes_validated_filter_search_and_safe_sort() -> None:
    repository = FakeRepository()
    service = make_list_service(repository)
    query = OwnerCredentialListQuery(
        student_id="B2203243",
        graduation_year=2023,
        status=OwnerCredentialStatus.UNCLAIMED,
        search="[Nguyen]",
        sort="student_id:asc",
    )

    await service.list_credentials(owner=make_owner(), query=query)

    assert repository.list_arguments is not None
    assert repository.list_arguments["status"] == OwnerCredentialStatus.UNCLAIMED
    assert repository.list_arguments["search"] == "[Nguyen]"
    assert repository.list_arguments["sort_field"] == "student_id"
    assert repository.list_arguments["sort_direction"] == 1


def test_list_rejects_invalid_sort_and_pagination() -> None:
    with pytest.raises(ValueError):
        OwnerCredentialListQuery(sort="national_id_hash:asc")
    with pytest.raises(ValueError):
        OwnerCredentialListQuery(page=0)
    with pytest.raises(ValueError):
        OwnerCredentialListQuery(limit=101)


def test_api_rejects_invalid_sort_and_credential_id() -> None:
    app.dependency_overrides[require_current_active_owner] = make_owner
    client = TestClient(app)
    try:
        invalid_sort = client.get(
            "/api/v1/owner/credentials",
            params={"sort": "national_id_hash:asc"},
        )
        invalid_id = client.get(
            "/api/v1/owner/credentials/not-an-object-id",
        )
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert invalid_sort.status_code == 422
    assert invalid_sort.json()["error_code"] == "VALIDATION_ERROR"
    assert invalid_id.status_code == 422
    assert invalid_id.json()["error_code"] == "VALIDATION_ERROR"


def test_openapi_advertises_endpoint_specific_error_statuses() -> None:
    paths = app.openapi()["paths"]

    assert set(paths["/api/v1/owner/credentials"]["get"]["responses"]) == {
        "200",
        "401",
        "403",
        "422",
        "500",
    }
    assert set(
        paths["/api/v1/owner/credentials/{credential_id}"]["get"]["responses"]
    ) == {
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
    }
    assert set(
        paths["/api/v1/owner/claim/credentials/{credential_id}"]["post"]["responses"]
    ) == {
        "200",
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }
    list_forbidden = paths["/api/v1/owner/credentials"]["get"]["responses"]["403"]
    detail_forbidden = paths[
        "/api/v1/owner/credentials/{credential_id}"
    ]["get"]["responses"]["403"]
    claim_forbidden = paths[
        "/api/v1/owner/claim/credentials/{credential_id}"
    ]["post"]["responses"]["403"]

    assert "CREDENTIAL_NOT_MATCHED" not in list_forbidden["description"]
    assert "CREDENTIAL_NOT_MATCHED" not in detail_forbidden["description"]
    assert "CREDENTIAL_NOT_MATCHED" in claim_forbidden["description"]


def test_list_http_happy_path_serializes_both_authorized_groups(
    monkeypatch,
) -> None:
    response_data = OwnerCredentialListData(
        summary=OwnerCredentialSummary(
            total_credentials=2,
            total_claimed=1,
            total_unclaimed=1,
        ),
        items=[
            OwnerCredentialListItem(
                id=str(CREDENTIAL_ID),
                student_id="B2203243",
                full_name="Nguyen Van A",
                graduation_year=2023,
                status="claimed",
                can_claim=False,
                claimed_at=NOW,
            ),
            OwnerCredentialListItem(
                id="507f1f77bcf86cd799439015",
                student_id="B2203244",
                full_name="Nguyen Van A",
                graduation_year=2024,
                status="unclaimed",
                can_claim=True,
                claimed_at=None,
            ),
        ],
        pagination=OwnerCredentialPagination(
            page=1,
            limit=20,
            total_items=2,
            total_pages=1,
        ),
    )
    list_mock = AsyncMock(return_value=response_data)
    monkeypatch.setattr(
        owner_credential_list_service,
        "list_credentials",
        list_mock,
    )
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).get("/api/v1/owner/credentials")
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert [item["status"] for item in body["data"]["items"]] == [
        "claimed",
        "unclaimed",
    ]
    assert "national_id_hash" not in response.text


def test_detail_http_happy_path_serializes_safe_fields(monkeypatch) -> None:
    detail_mock = AsyncMock(
        return_value=OwnerCredentialDetail(
            id=str(CREDENTIAL_ID),
            issuer_org_id=str(ISSUER_ID),
            issuer=OwnerCredentialIssuerDetail(
                id=str(ISSUER_ID),
                name="Lucidex University",
                address="1 Education Street",
                contact_email="contact@lucidex.edu.vn",
                contact_phone="02812345678",
            ),
            student_id="B2203243",
            full_name="Nguyen Van A",
            dob=date(2001, 1, 1),
            major="Computer Science",
            graduation_year=2023,
            classification="Good",
            university_email="student@example.edu",
            phone="0912345678",
            status="claimed",
            claim_method="manual",
            claimed_at=NOW,
        )
    )
    monkeypatch.setattr(
        owner_credential_detail_service,
        "get_credential",
        detail_mock,
    )
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).get(f"/api/v1/owner/credentials/{CREDENTIAL_ID}")
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["phone"] == "0912345678"
    assert response.json()["data"]["issuer"] == {
        "id": str(ISSUER_ID),
        "name": "Lucidex University",
        "address": "1 Education Street",
        "contact_email": "contact@lucidex.edu.vn",
        "contact_phone": "02812345678",
    }
    assert "national_id_hash" not in response.text
    assert "tax_code" not in response.text


def test_claim_http_happy_path_serializes_idempotency(monkeypatch) -> None:
    claim_mock = AsyncMock(
        return_value=ClaimCredentialData(
            credential=ClaimedCredentialData(
                id=str(CREDENTIAL_ID),
                status="claimed",
                claim_method="manual",
                claimed_at=NOW,
            ),
            already_claimed=False,
        )
    )
    monkeypatch.setattr(
        owner_credential_claim_service,
        "claim_credential",
        claim_mock,
    )
    app.dependency_overrides[require_current_active_owner] = make_owner
    try:
        response = TestClient(app).post(
            f"/api/v1/owner/claim/credentials/{CREDENTIAL_ID}",
            json={},
        )
    finally:
        app.dependency_overrides.pop(require_current_active_owner, None)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["already_claimed"] is False
    assert "national_id_hash" not in response.text


@pytest.mark.parametrize(
    "owner",
    [
        make_owner(status=OwnerStatus.PENDING),
        make_owner(status=OwnerStatus.LOCKED_MIGRATED),
        make_owner(status=OwnerStatus.SOFT_DELETED),
        make_owner(deleted_at=NOW),
    ],
)
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/v1/owner/credentials", None),
        ("get", f"/api/v1/owner/credentials/{CREDENTIAL_ID}", None),
        (
            "post",
            f"/api/v1/owner/claim/credentials/{CREDENTIAL_ID}",
            {},
        ),
    ],
)
def test_owner_lifecycle_blocks_every_credential_route(
    owner: Owner,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    app.dependency_overrides[require_current_actor] = lambda: (
        owner,
        object(),
        "owner",
    )
    try:
        response = TestClient(app).request(method, path, json=body)
    finally:
        app.dependency_overrides.pop(require_current_actor, None)

    assert response.status_code == 403
    assert response.json()["error_code"] == "OWNER_INACTIVE"


class AggregateCursor:
    async def to_list(self, *, length: int) -> list[dict[str, Any]]:
        assert length == 1
        return [{"items": [], "summary": []}]


class AggregateCollection:
    def __init__(self) -> None:
        self.pipeline: list[dict[str, Any]] | None = None

    def aggregate(self, pipeline: list[dict[str, Any]]) -> AggregateCursor:
        self.pipeline = pipeline
        return AggregateCursor()


@pytest.mark.asyncio
async def test_repository_applies_scope_before_escaped_search(monkeypatch) -> None:
    collection = AggregateCollection()
    monkeypatch.setattr(
        Credential,
        "get_motor_collection",
        classmethod(lambda cls: collection),
    )

    await CredentialRepository().list_for_owner(
        owner_id=OWNER_ID,
        verified_national_id_hash=VERIFIED_HASH,
        page=1,
        limit=20,
        student_id=None,
        graduation_year=None,
        status=None,
        search="[Nguyen]",
        sort_field="_id",
        sort_direction=-1,
    )

    assert collection.pipeline is not None
    match_query = collection.pipeline[0]["$match"]
    assert match_query["$and"][0] == build_owner_credential_scope(
        owner_id=OWNER_ID,
        verified_national_id_hash=VERIFIED_HASH,
    )
    search_scope = match_query["$and"][1]["$or"]
    assert all(
        field_query["$regex"] == r"\[Nguyen\]"
        for condition in search_scope
        for field_query in condition.values()
    )
    assert collection.pipeline[1].get("$facet") is not None


class EmptyAggregateCursor:
    async def to_list(self, *, length: int) -> list[dict[str, Any]]:
        assert length == 1
        return []


class RecordingFindCollection:
    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []
        self.pipelines: list[list[dict[str, Any]]] = []

    def aggregate(self, pipeline: list[dict[str, Any]]) -> EmptyAggregateCursor:
        self.pipelines.append(pipeline)
        return EmptyAggregateCursor()

    async def find_one(
        self,
        query: dict[str, Any],
        projection: dict[str, Any],
    ) -> None:
        assert projection
        self.queries.append(query)
        return None


@pytest.mark.asyncio
async def test_detail_claim_state_and_ekyc_queries_exclude_deleted(
    monkeypatch,
) -> None:
    collection = RecordingFindCollection()
    monkeypatch.setattr(
        Credential,
        "get_motor_collection",
        classmethod(lambda cls: collection),
    )
    repository = CredentialRepository()

    assert (
        await repository.get_for_owner(
            credential_id=CREDENTIAL_ID,
            owner_id=OWNER_ID,
            verified_national_id_hash=VERIFIED_HASH,
        )
        is None
    )
    assert await repository.get_claim_state(CREDENTIAL_ID) is None
    assert await repository.has_unclaimed_national_id_hash(VERIFIED_HASH) is False

    detail_pipeline = collection.pipelines[0]
    detail_scope = detail_pipeline[0]["$match"]["$and"][1]
    assert detail_scope["deleted_at"] is None
    lookup = detail_pipeline[1]["$lookup"]
    assert lookup["from"] == "organizations"
    assert lookup["localField"] == "issuer_org_id"
    assert lookup["foreignField"] == "_id"
    assert lookup["pipeline"][0]["$project"] == {
        "_id": 1,
        "name": 1,
        "address": 1,
        "contact_email": 1,
        "contact_phone": 1,
    }
    assert collection.queries[0] == {
        "_id": CREDENTIAL_ID,
        "deleted_at": None,
    }
    assert collection.queries[1] == {
        "deleted_at": None,
        "status": "unclaimed",
        "owner_id": None,
        "national_id_hash": VERIFIED_HASH,
    }


@pytest.mark.asyncio
async def test_detail_maps_actual_fields_and_excludes_hash() -> None:
    repository = FakeRepository()
    repository.detail = detail_record()
    service = make_detail_service(repository)

    detail = await service.get_credential(
        owner=make_owner(),
        credential_id=CREDENTIAL_ID,
    )

    assert detail.major == "Computer Science"
    assert detail.major_vi == "Khoa học máy tính"
    assert detail.major_en == "Computer Science"
    assert detail.degree_type == "Bachelor of Engineering"
    assert detail.classification == "Good"
    assert detail.graduation_classification_vi == "Giỏi"
    assert detail.graduation_classification_en == "Good"
    assert detail.phone == "0912345678"
    assert detail.issuer is not None
    assert detail.issuer.id == str(ISSUER_ID)
    assert detail.issuer.name == "Lucidex University"
    assert detail.issuer.contact_email == "contact@lucidex.edu.vn"
    assert "national_id_hash" not in detail.model_dump_json()
    assert "tax_code" not in detail.model_dump_json()
    assert "created_at" not in detail.model_dump_json()
    assert repository.detail_arguments == {
        "credential_id": CREDENTIAL_ID,
        "owner_id": OWNER_ID,
        "verified_national_id_hash": VERIFIED_HASH,
    }


@pytest.mark.asyncio
async def test_detail_uses_default_degree_type_for_legacy_record() -> None:
    repository = FakeRepository()
    repository.detail = detail_record(degree_type=None)
    service = make_detail_service(repository)

    detail = await service.get_credential(
        owner=make_owner(),
        credential_id=CREDENTIAL_ID,
    )

    assert detail.degree_type == "Bằng tốt nghiệp đại học"


@pytest.mark.asyncio
async def test_detail_outside_scope_is_not_found() -> None:
    repository = FakeRepository()
    service = make_detail_service(repository)

    with pytest.raises(AppError) as exc_info:
        await service.get_credential(
            owner=make_owner(),
            credential_id=CREDENTIAL_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "CREDENTIAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_claim_success_uses_verified_owner_and_atomic_repository_call() -> None:
    repository = FakeRepository()
    repository.claimed = {
        "_id": CREDENTIAL_ID,
        "status": "claimed",
        "claim_method": "manual",
        "claimed_at": NOW,
    }
    service = make_claim_service(repository)

    data = await service.claim_credential(
        owner=make_owner(),
        credential_id=CREDENTIAL_ID,
    )

    assert data.already_claimed is False
    assert data.credential.claim_method == "manual"
    assert repository.claim_arguments is not None
    assert repository.claim_arguments["owner_id"] == OWNER_ID
    assert repository.claim_arguments["verified_national_id_hash"] == VERIFIED_HASH


@pytest.mark.asyncio
async def test_claim_is_idempotent_for_same_owner() -> None:
    repository = FakeRepository()
    repository.claim_state = {
        "_id": CREDENTIAL_ID,
        "owner_id": OWNER_ID,
        "status": "claimed",
        "claim_method": "manual",
        "claimed_at": NOW,
    }
    service = make_claim_service(repository)

    data = await service.claim_credential(
        owner=make_owner(),
        credential_id=CREDENTIAL_ID,
    )

    assert data.already_claimed is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("owner", "expected_detail", "expected_error_code"),
    [
        (
            make_owner(status=OwnerStatus.PENDING),
            "Active owner account is required.",
            "OWNER_INACTIVE",
        ),
        (
            make_owner(),
            "eKYC verification is required.",
            "EKYC_NOT_VERIFIED",
        ),
    ],
)
async def test_claim_rejects_owner_without_required_state(
    owner: Owner,
    expected_detail: str,
    expected_error_code: str,
) -> None:
    service = make_claim_service(FakeRepository(), identity_hash=None)

    with pytest.raises(AppError) as exc_info:
        await service.claim_credential(
            owner=owner,
            credential_id=CREDENTIAL_ID,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.message == expected_detail
    assert exc_info.value.error_code == expected_error_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected_status", "expected_error_code"),
    [
        (None, 404, "CREDENTIAL_NOT_FOUND"),
        (
            {
                "_id": CREDENTIAL_ID,
                "owner_id": OTHER_OWNER_ID,
                "status": "claimed",
            },
            409,
            "CREDENTIAL_ALREADY_CLAIMED",
        ),
        (
            {
                "_id": CREDENTIAL_ID,
                "owner_id": None,
                "status": "unclaimed",
                "national_id_hash": "different-hash",
            },
            403,
            "CREDENTIAL_NOT_MATCHED",
        ),
    ],
)
async def test_claim_classifies_atomic_miss(
    state: dict[str, Any] | None,
    expected_status: int,
    expected_error_code: str,
) -> None:
    repository = FakeRepository()
    repository.claim_state = state
    service = make_claim_service(repository)

    with pytest.raises(AppError) as exc_info:
        await service.claim_credential(
            owner=make_owner(),
            credential_id=CREDENTIAL_ID,
        )

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.error_code == expected_error_code
    if expected_error_code == "CREDENTIAL_NOT_MATCHED":
        assert (
            exc_info.value.message
            == "Credential does not belong to your verified identity."
        )


class AtomicFakeCollection:
    def __init__(self) -> None:
        self.document = {
            "_id": CREDENTIAL_ID,
            "owner_id": None,
            "status": "unclaimed",
            "national_id_hash": VERIFIED_HASH,
        }
        self.lock = asyncio.Lock()
        self.calls: list[tuple[dict[str, Any], dict[str, Any]]] = []

    async def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any] | None:
        async with self.lock:
            self.calls.append((query, update))
            if any(self.document.get(key) != value for key, value in query.items()):
                return None
            self.document.update(update["$set"])
            return {
                "_id": self.document["_id"],
                "status": self.document["status"],
                "claim_method": self.document["claim_method"],
                "claimed_at": self.document["claimed_at"],
            }


@pytest.mark.asyncio
async def test_concurrent_atomic_claim_only_mutates_once(monkeypatch) -> None:
    collection = AtomicFakeCollection()
    monkeypatch.setattr(
        Credential,
        "get_motor_collection",
        classmethod(lambda cls: collection),
    )
    repository = CredentialRepository()

    results = await asyncio.gather(
        repository.claim_for_owner(
            credential_id=CREDENTIAL_ID,
            owner_id=OWNER_ID,
            verified_national_id_hash=VERIFIED_HASH,
            claimed_at=NOW,
        ),
        repository.claim_for_owner(
            credential_id=CREDENTIAL_ID,
            owner_id=OTHER_OWNER_ID,
            verified_national_id_hash=VERIFIED_HASH,
            claimed_at=NOW,
        ),
    )

    assert sum(result is not None for result in results) == 1
    assert collection.document["owner_id"] in {OWNER_ID, OTHER_OWNER_ID}
    assert all(
        query["deleted_at"] is None
        and query["owner_id"] is None
        and query["status"] == "unclaimed"
        and query["national_id_hash"] == VERIFIED_HASH
        and update["$set"]["claim_method"] == "manual"
        for query, update in collection.calls
    )


@pytest.mark.asyncio
async def test_deleted_unclaimed_credential_is_not_mutated_by_claim(
    monkeypatch,
) -> None:
    collection = AtomicFakeCollection()
    collection.document["deleted_at"] = NOW
    original_document = collection.document.copy()
    monkeypatch.setattr(
        Credential,
        "get_motor_collection",
        classmethod(lambda cls: collection),
    )

    result = await CredentialRepository().claim_for_owner(
        credential_id=CREDENTIAL_ID,
        owner_id=OWNER_ID,
        verified_national_id_hash=VERIFIED_HASH,
        claimed_at=NOW,
    )

    assert result is None
    assert collection.document == original_document
    assert collection.calls[0][0]["deleted_at"] is None
