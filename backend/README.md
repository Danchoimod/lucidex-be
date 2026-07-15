# Lucidex Backend Developer Guide

## Overview

Lucidex is an API-first FastAPI backend using MongoDB Atlas and Beanie. It serves four portals: Admin, Issuer, Owner, and Verifier.

Startup flow:

```text
app/main.py
  -> loads core/config.py
  -> configures JSON logging and middleware
  -> connects to MongoDB Atlas
  -> initializes 16 Beanie document models and indexes
  -> mounts the /api/v1 routers
```

Application startup stops when MongoDB cannot be reached or authenticated.

## Environment Management

Lucidex has three named environments:

| Environment | Current use | Configuration |
|---|---|---|
| `development` | Local development | `backend/.env` |
| `staging` | Cloud Run for FE/QA | `deploy/staging.env.yaml` and Secret Manager |
| `production` | Reserved for the production release phase | `deploy/production.env.yaml` and separate secrets |

The backend reads only `backend/.env` locally. A repository-root `.env` is not loaded.

Create the local file from the template:

```powershell
Copy-Item .env.example .env
```

Required values:

```env
ENV=development
MONGODB_URI=<development-mongodb-uri>
MONGODB_DB_NAME=lucidex_dev
JWT_SECRET_KEY=<random-secret-at-least-32-characters>
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Never commit `.env`. Staging secrets such as `MONGODB_URI` and `JWT_SECRET_KEY` belong in Google Secret Manager, not in YAML, source code, build arguments, or command history.

## Local Development

From `backend/`:

```powershell
uv run fastapi dev app/main.py
```

Local URLs:

| URL | Purpose |
|---|---|
| `/health` | Process health check |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI schema |

Quality checks:

```powershell
uv run ruff check app scripts tests
uv run pytest
```

Current smoke tests cover API health, successful Issuer registration, field validation errors, and duplicate tax-code errors.

## Code Organization

```text
app/
  api/v1/       HTTP routing grouped by portal
  core/         configuration, database, JWT, middleware, logging
  models/       Beanie documents and MongoDB indexes
  schemas/      Pydantic request and response DTOs
  services/     business logic and database operations
  utils/        shared normalization and validation helpers
  workers/      future ARQ background workers
```

Request flow:

```text
Router -> Schema -> Service -> Beanie Model -> MongoDB
```

Routers should handle HTTP concerns only. Business rules and database queries belong in services. Do not return database documents directly when responses must hide internal fields.

## Database

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

Synchronize model indexes from `backend/`:

```powershell
uv run python scripts/create_indexes.py
```

MongoDB does not use Alembic. Test index changes in staging before production. Once production contains real data, use controlled index/data migrations instead of deleting collections.

## API Conventions

Business routes use:

```text
/api/v1/admin/...
/api/v1/issuer/...
/api/v1/owner/...
/api/v1/verifier/...
```

Responses use one envelope:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully.",
  "error_code": null
}
```

Validation errors return safe field-level details in `data.errors` without echoing input values.

Available business endpoint:

```http
POST /api/v1/issuer/register
```

It normalizes and validates registration data, rejects duplicate live Issuer tax codes, and creates an organization with `pending_review` status.

## Logging and Sensitive Data

`RequestLoggingMiddleware` creates an `X-Request-ID` and emits structured JSON logs containing method, path, status, latency, and actor type when available.

Never log request bodies, passwords, password hashes, OTP values, JWTs, raw national IDs, or eKYC images.

## Current QA Deployment Workflow

The current goal is only to deploy the API to Cloud Run staging for FE/QA. Production deployment automation will be added when the team starts production releases.

Current workflow:

```text
Code and test locally
  -> push feature branch to GitHub
  -> Pull Request and merge into develop
  -> build image from develop
  -> deploy Cloud Run staging
  -> send staging URL to FE/QA
  -> FE/QA reports "Staging OK"
  -> developer reviews and merges develop into main
```

### One-time Google Cloud setup

Authenticate and select the project:

```powershell
gcloud auth login
gcloud config set project "<project-id>"
gcloud config set run/region "asia-southeast1"
```

Enable services:

```powershell
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com
```

Create these resources once:

```text
Artifact Registry: lucidex
Cloud Run service: lucidex-api-staging
Service account: lucidex-api-staging@<project-id>.iam.gserviceaccount.com
Secret: lucidex-staging-mongodb-uri
Secret: lucidex-staging-jwt-secret
```

Grant the staging service account `roles/secretmanager.secretAccessor` on the two staging secrets. Configure a staging Atlas database user and allow Cloud Run network access.

Update `deploy/staging.env.yaml` with the real staging frontend URL before deploying. Do not put secrets in this file.

### Deploy a version for QA

1. Code and test locally:

   ```powershell
   Set-Location backend
   uv run ruff check app scripts tests
   uv run pytest
   uv run fastapi dev app/main.py
   ```

   Verify `/health`, `/docs`, and every changed endpoint. Stop the local server, then return to the repository root:

   ```powershell
   Set-Location ..
   ```

2. Review, commit, and push the feature branch yourself:

   ```powershell
   git status
   git diff
   git add <changed-files>
   git commit -m "feat: <describe-the-change>"
   git push -u origin <feature-branch>
   ```

   Create a Pull Request on GitHub and merge the reviewed feature branch into `develop`.

3. Update the local `develop` branch:

   ```powershell
   git switch develop
   git pull --ff-only origin develop
   git status --short
   ```

   The working tree must be clean before building.

4. Build the image from the repository root:

   ```powershell
   .\backend\deploy\build-image.ps1 `
     -ProjectId "<project-id>" `
     -Region "asia-southeast1"
   ```

   Clean builds use the Git commit SHA as the image tag. `-AllowDirty` is available only for temporary QA experiments and adds `-dirty-<timestamp>` to the tag.

5. Deploy staging using numeric Secret Manager versions:

   ```powershell
   .\backend\deploy\deploy-cloud-run.ps1 `
     -ProjectId "<project-id>" `
     -Region "asia-southeast1" `
     -MongoSecretVersion "1" `
     -JwtSecretVersion "1"
   ```

   The script reads the image URI saved by the build script, deploys `lucidex-api-staging`, runs `/health`, and prints the URL to share with FE/QA.

6. Retrieve and share the staging URL if needed:

   ```powershell
   $STAGING_URL = gcloud run services describe lucidex-api-staging `
     --project="<project-id>" `
     --region="asia-southeast1" `
     --format="value(status.url)"

   $STAGING_URL
   ```

   Share:

   ```text
   API:     <staging-url>
   Swagger: <staging-url>/docs
   OpenAPI: <staging-url>/openapi.json
   ```

7. FE/QA verifies:

   - `/health`, `/docs`, and `/openapi.json`.
   - The frontend can call the API and CORS works.
   - Changed endpoints return the expected response envelope.
   - Validation failures return the expected `422` details.
   - Duplicate business data returns the expected `409` response.
   - Data is written correctly to the staging database.

8. When testing passes, FE/QA posts a short message in the team channel or Pull Request:

   ```text
   Staging OK.
   FE/QA testing is complete.
   The change can be merged into main.
   ```

9. A developer reviews and manually merges `develop` into `main`. The scripts do not switch branches, create commits, push code, or merge Pull Requests.

If the project does not have real production users yet, stop here. Add production deployment only when the leader confirms that the project is ready to go live.

Keep these rules even in the simplified workflow:

- Never commit secrets.
- Staging must use a separate database and database user.
- Never release production code that was not tested in staging.

Read staging logs:

```powershell
gcloud run services logs read lucidex-api-staging `
  --region "asia-southeast1" `
  --limit 100
```

If PowerShell blocks repository scripts, allow them for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Common QA Deployment Failures

| Symptom | Likely cause |
|---|---|
| Build script refuses to run | Uncommitted files; commit them or use `-AllowDirty` for temporary QA only |
| Revision is not ready | Missing configuration or MongoDB startup failure |
| MongoDB authentication failed | Wrong Atlas credentials or secret version |
| MongoDB selection timeout | Atlas Network Access blocks Cloud Run |
| Secret permission denied | Staging service account cannot access the secret |
| Browser CORS error | Wrong frontend origin in `staging.env.yaml` |
| Placeholder validation fails | Replace `example.com` in the staging YAML |

## Sources of Truth

Implement business behavior according to the documents in `../docs/`. Do not invent pending authentication, claim, verification, consent, CSV, or administration workflows.
