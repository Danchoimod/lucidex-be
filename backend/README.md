# Lucidex Backend

FastAPI API backed by MongoDB Atlas and Beanie ODM.

## Local setup

1. Copy `backend/.env.example` to `backend/.env` and provide real secrets.
2. Install dependencies from the repository root with `uv sync`.
3. Run `uv run --project backend fastapi dev app/main.py`.
4. Open `http://127.0.0.1:8000/docs`.

The application creates declared Beanie indexes during startup. Business routes remain TODO and are organized under `/api/v1/{admin,issuer,owner,verifier}`.
