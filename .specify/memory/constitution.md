# Lucidex Backend Constitution

## I. Feature-Module Layering (NON-NEGOTIABLE)

Every new feature lives under `src/<module>/` and follows strict dependency flow:

```
Router → Schema → Service → Beanie Model → MongoDB
```

- **Routers** are thin: validate input via Pydantic schemas, call a service, return `ApiResponse[T]`. No business logic, no direct Beanie queries.
- **Services** own all business logic and all database queries.
- **Schemas** are pure Pydantic DTOs — separate from Beanie Document classes.
- Never skip or collapse layers. A router that queries Mongo directly is a violation.

## II. API Response Envelope (NON-NEGOTIABLE)

Every endpoint returns `ApiResponse[T]` from `src.schemas.common`:

```python
class ApiResponse(BaseModel, Generic[DataT]):
    success: bool
    data: DataT | None = None
    message: str | None = None
    error_code: str | None = None
```

- Successful responses: `success=True`, `error_code=None` explicitly set.
- Every `@router` decorator must declare `response_model`, `status_code`, `summary`, `description`.
- `summary` is prefixed with the portal name: `[Issuer]`, `[Admin]`, `[Owner]`, `[Verifier]`.

## III. Error Handling

- Expected domain errors: one `AppError` subclass per distinct error case, in `<module>/exceptions.py`.
- Each has a human-readable `message` and machine-readable `error_code` in `UPPER_SNAKE_CASE`.
- Shared infrastructure auth failures (`dependencies.py`, `token.py`): use `HTTPException`.
- Unhandled exceptions return `INTERNAL_SERVER_ERROR` — never leak internals.

## IV. Naming Conventions

- **Files/folders**: `snake_case`. Module names are singular (`credential/`, not `credentials/`).
- **Classes**: `PascalCase`. Beanie documents are singular nouns.
- **Functions**: `snake_case`, verb-first (`create_access_token`, `hash_imported_national_id`).
- **Constants**: `UPPER_SNAKE_CASE`.
- **Enums**: `StrEnum` with `UPPER_SNAKE_CASE` members (not plain `Enum`).

## V. Beanie / MongoDB Models

- Every `Document` has an inner `class Settings` with `name` (plural snake_case collection) and `indexes`.
- Use `PydanticObjectId` for references. Timestamps: `datetime` with `Field(default_factory=utc_now)`.
- Status fields: `Literal["a", "b"]` inside Documents, not enums.
- New models must be added to `DOCUMENT_MODELS` list in `src/database.py`.

## VI. Imports

- Always absolute: `from src.config import settings`. Never relative imports.
- Order (Ruff-enforced): stdlib → third-party → local (`src.*`).
- No barrel re-exports for models/services — import the specific submodule.

## VII. Testing

- Framework: Pytest + pytest-asyncio (`asyncio_mode = auto`).
- Tests mirror source: `backend/tests/<module>/test_<thing>.py`.
- DB tests use `{DB_NAME}-test` database, wiped after each test.
- Sync endpoint tests: `TestClient(app)`. No mocking framework currently in use.

## VIII. Logging & Security

- JSON structured logs via `JsonFormatter`. Logger names: `logging.getLogger("lucidex.<area>")` or `logging.getLogger(__name__)`.
- Only fields in `LOG_FIELDS` may appear in `extra={}`. Never add new fields without registering them.
- **Never log**: passwords, OTPs, JWT tokens, raw national IDs, ID card images, raw request bodies.

## Governance

This constitution captures the conventions extracted from the Lucidex backend codebase as of 2026-08-09. It mirrors the `## Code Style Guide (strict)` section of `AGENTS.md` at the repo root — **AGENTS.md is the source of truth**. If they ever conflict, AGENTS.md wins. Update both together when a new pattern is intentionally introduced.

All implementation plans (`plan.md`), tasks (`tasks.md`), and generated code must comply with this constitution before being approved or merged.

**Version**: 1.0 | **Ratified**: 2026-08-09 | **Last Amended**: 2026-08-09
