# Lucidex

This repository contains the Lucidex FastAPI backend. The frontend is maintained in a separate repository.

## Stack

- Python 3.11+
- FastAPI
- MongoDB Atlas
- Beanie ODM and Pydantic v2
- Motor
- ARQ and Redis for future background jobs

## Run locally

```powershell
Copy-Item backend/.env.example backend/.env
uv sync
uv run --project backend fastapi dev app/main.py
```

Provide real MongoDB and JWT secrets before starting. API documentation is available at `http://127.0.0.1:8000/docs`, and health status at `http://127.0.0.1:8000/health`.

Business and schema requirements are preserved in `docs/`. The developer scratch file `note-run.md` is intentionally retained.
