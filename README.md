# Lucidex Backend

Lucidex is an API-first digital credential verification platform. This repository contains only the backend; the frontend is maintained in a separate repository.

The backend provides the technical foundation for four portals:

- Issuer: institutions that issue credentials.
- Owner: credential owners.
- Verifier: organizations that verify credentials.
- Admin: platform administrators.

## Current Status

The backend scaffold, MongoDB Atlas connection, 16 Beanie documents, database indexes, JWT foundation, portal router structure, structured logging, detailed validation responses, and public Issuer registration are complete. Business logic for authentication, claims, verification, CSV uploads, consent, and administration remains pending and will be implemented according to the acceptance criteria in `docs/`.

The currently available endpoints are:

```http
GET /health
GET /api/v1/{admin|issuer|owner|verifier}/health
POST /api/v1/issuer/register
```

Business APIs will be organized under:

```text
/api/v1/admin/...
/api/v1/issuer/...
/api/v1/owner/...
/api/v1/verifier/...
```

## Technology Stack

- Python 3.11+
- FastAPI and Pydantic v2
- MongoDB Atlas
- Beanie ODM 1.x and Motor
- PyJWT
- pwdlib with Argon2 and Bcrypt
- ARQ and Redis for future background jobs
- uv for dependency and environment management
- Ruff and Pytest for quality checks

Beanie is restricted to the `1.x` release line because the current architecture uses Motor.

## Repository Structure

```text
Lucidex/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Routers for Admin, Issuer, Owner, and Verifier
│   │   ├── core/            # Configuration, MongoDB, JWT, dependencies, logging
│   │   ├── models/          # 16 Beanie documents
│   │   ├── schemas/         # Pydantic request and response DTOs
│   │   ├── services/        # Business logic
│   │   ├── utils/           # Non-business utility functions
│   │   ├── workers/         # ARQ workers
│   │   └── main.py          # FastAPI entry point
│   ├── scripts/             # Index creation and Admin seed scripts
│   ├── tests/
│   ├── .env.example
│   ├── Dockerfile
│   └── pyproject.toml
├── docs/                    # Master prompt, database schema, acceptance criteria
├── note-run.md              # Personal development notes
├── pyproject.toml           # uv workspace configuration
└── uv.lock
```

## Local Development

### 1. Prerequisites

- Python 3.11 or newer.
- uv.
- A MongoDB Atlas cluster and valid Database User.
- Your development IP address added to Atlas Network Access.

### 2. Create the Environment File

From the repository root:

```powershell
Copy-Item backend/.env.example backend/.env
```

At minimum, configure:

```env
ENV=development
MONGODB_URI=mongodb+srv://<db_user>:<encoded_password>@<cluster>/?appName=Lucidex
MONGODB_DB_NAME=lucidex_dev
JWT_SECRET_KEY=<random-secret-at-least-32-characters>
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Never commit `.env`. If the MongoDB password contains special characters such as `@`, `#`, `%`, or `/`, URL-encode it before adding it to the URI.

### 3. Install Dependencies

```powershell
uv sync
```

### 4. Start the Backend

```powershell
Set-Location backend
uv run fastapi dev app/main.py
```

After a successful startup:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## Quality Checks

Run these commands from `backend/`:

```powershell
uv run ruff check app scripts tests
uv run pytest
```

Create or synchronize the indexes declared by the Beanie models:

```powershell
uv run python scripts/create_indexes.py
```

## API Development Guidelines

The standard dependency flow is:

```text
Router → Schema → Service → Beanie Model → MongoDB
```

- HTTP endpoints: `backend/app/api/v1/<portal>/`.
- Request and response DTOs: `backend/app/schemas/`.
- Business logic and database queries: `backend/app/services/`.
- MongoDB documents: `backend/app/models/`.
- Shared technical helpers: `backend/app/utils/`.
- Authentication, configuration, and logging: `backend/app/core/`.
- Tests mirror the application structure under `backend/tests/`.

Do not place complex queries or business logic directly in routers. Tenant-scoped queries must derive `org_id` or the owner identity from the JWT instead of trusting values supplied by clients.

## Response Format

APIs use a consistent response envelope:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully.",
  "error_code": null
}
```

Validation failures use the same envelope and include safe field-level details in `data.errors`. Input values are never echoed in validation responses.

## Environments and Cloud Run

Lucidex uses three runtime environments:

- `development`: local development with debug logging and mock integrations.
- `staging`: Cloud Run environment used by frontend and QA.
- `production`: public Cloud Run environment with production secrets and integrations.

The Dockerfile in `backend/` is compatible with the Cloud Run container contract and reads the injected `PORT` variable. Deploy from the repository root with `backend/` as the source directory:

```powershell
gcloud run deploy lucidex-api --source backend --region <region>
```

Store `MONGODB_URI`, `JWT_SECRET_KEY`, and provider credentials in Google Secret Manager. Do not include `.env` in a container image or deployment source archive.

## Logging and Sensitive Data

Application logs are emitted as JSON and contain a request ID, method, path, status code, latency, and actor type when a valid JWT is available.

Never log:

- Passwords or password hashes.
- OTP values.
- JWT access or refresh tokens.
- Raw national ID values.
- ID card or selfie images.
- Raw request bodies containing sensitive data.

## Sources of Truth

- `docs/lucidex_master_prompt.md`
- `docs/lucidex_db_schema.md`
- `docs/lucidex_ac_admin.md`
- `docs/lucidex_ac_issuer.md`
- `docs/lucidex_ac_owner.md`
- `docs/lucidex_ac_verifier.md`

If the schema conflicts with an acceptance criterion, prioritize the acceptance criterion and explicitly document the technical decision instead of making an implicit assumption.

See [`backend/README.md`](backend/README.md) for the detailed backend developer guide.
