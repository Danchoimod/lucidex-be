# Lucidex Backend Developer Guide

## Entry Point and Startup Flow

The FastAPI entry point is `app/main.py`.

```text
app/main.py
  ├── loads settings from core/config.py
  ├── configures JSON logging
  ├── registers middleware and exception handlers
  ├── runs the lifespan handler from core/database.py
  │     ├── pings MongoDB Atlas
  │     └── initializes Beanie with 16 document models
  └── mounts api/v1/router.py
```

If MongoDB cannot be reached or authentication fails, application startup stops instead of serving APIs without a working database.

## Environment Configuration

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Required variables:

| Variable | Purpose |
|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | Lucidex database name |
| `JWT_SECRET_KEY` | JWT signing secret with at least 32 characters |

Other configuration groups cover JWT lifetimes, Redis, SMTP/SMS, eKYC mock/provider settings, file storage, and CORS. Never hardcode or log secrets.

Supported runtime environments are `development`, `staging`, and `production`.

`core/config.py` gives priority to `backend/.env`. The repository-root `.env` remains supported for compatibility with the earlier development environment.

## Running the Application

From the `backend/` directory:

```powershell
uv run fastapi dev app/main.py
```

Important URLs:

| URL | Purpose |
|---|---|
| `/health` | API process health check |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI schema for frontend and client generation |

## Code Organization

### Routers

Create endpoints under the portal that consumes them:

```text
app/api/v1/admin/
app/api/v1/issuer/
app/api/v1/owner/
app/api/v1/verifier/
```

For example, an Owner credential API should be placed in:

```text
app/api/v1/owner/credentials.py
```

Then include its router from `app/api/v1/owner/router.py`.

### Schemas

Pydantic DTOs belong in `app/schemas/`. Do not return a database document directly when the response must hide internal or sensitive fields.

### Services

Business logic and database queries belong in `app/services/`. Routers should only handle HTTP validation, call services, and map results to responses.

### Models

Each MongoDB collection has its own Beanie document in `app/models/`. Add every new document to `DOCUMENT_MODELS` in `app/models/__init__.py` so Beanie can initialize its collection and indexes.

### Core and Utilities

- `app/core/`: configuration, database, JWT, FastAPI dependencies, and logging.
- `app/utils/`: small technical helpers that do not depend on HTTP or contain business workflows.

## Database Collections

The backend declares 16 collections:

```text
organizations             institution_accounts
platform_admins           owners
credentials               claims
csv_upload_jobs           csv_upload_rows
verified_links            access_records
trusted_organizations     notifications
audit_logs                otp_codes
sessions                  ekyc_capture_sessions
```

The Beanie models declare unique, compound, partial, and TTL indexes according to `docs/lucidex_db_schema.md`.

Synchronize indexes manually with:

```powershell
uv run python scripts/create_indexes.py
```

MongoDB does not use Alembic. Schema changes must be handled through model/index scripts or dedicated data migration scripts after real data exists.

## Authentication and Tenant Isolation

An access token is expected to contain:

```json
{
  "sub": "actor-id",
  "actor_type": "owner|issuer|verifier|admin",
  "org_id": "organization-id-or-null",
  "session_id": "session-id",
  "permissions": []
}
```

Actor and permission dependencies live in `app/core/deps.py`. Every Issuer or Verifier query must be scoped by the `org_id` from the token. Never trust an `org_id` supplied by the client.

## Logging

`RequestLoggingMiddleware` generates or accepts an `X-Request-ID`, includes it in the response headers, and emits one JSON log for every request.

Log levels:

- `INFO`: successful 2xx and 3xx requests.
- `WARNING`: 4xx responses and validation errors.
- `ERROR`: 5xx responses and unhandled exceptions.
- `DEBUG`: enabled when `ENV=development`.

Do not log request bodies, passwords, OTP values, tokens, raw national IDs, or eKYC images.

## Tests

Tests should mirror the application structure:

```text
tests/
├── api/v1/admin/
├── api/v1/issuer/
├── api/v1/owner/
├── api/v1/verifier/
├── services/
├── models/
└── utils/
```

Run all quality checks with:

```powershell
uv run ruff check app scripts tests
uv run pytest
```

## Implementation Status

Completed:

- MongoDB Atlas, Motor, and Beanie startup.
- 16 document models and their indexes.
- JWT and security foundation.
- Router skeletons for all four portals.
- Shared response envelope.
- Field-level validation error responses without echoing input values.
- Structured request and error logging.
- Health endpoint and OpenAPI generation.
- Public Issuer registration with normalization, validation, duplicate tax-code protection, and `pending_review` creation.
- Cloud Run-compatible Dockerfile.

Not implemented during the cleanup phase:

- Complete authentication, 2FA, and refresh-token rotation.
- Remaining Admin, Issuer, Owner, and Verifier business endpoints.
- CSV processing workers.
- Claim, eKYC, and consent workflows.
- Platform Admin seed logic.
- Business test suites.

Do not invent these workflows. Implement them incrementally according to the source documents in `../docs/`.

## Cloud Run Deployment

Build and deploy from the repository root with `backend/` as the source directory:

```powershell
gcloud run deploy lucidex-api --source backend --region <region>
```

Cloud Run supplies the `PORT` environment variable. Configure non-sensitive values such as `ENV`, `MONGODB_DB_NAME`, and `CORS_ALLOWED_ORIGINS` as service environment variables. Load `MONGODB_URI`, `JWT_SECRET_KEY`, and provider credentials from Google Secret Manager.
