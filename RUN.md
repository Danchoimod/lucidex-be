## Lệnh chạy dự án
uv run uvicorn src.main:app --reload
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
cd backend

python bump_version.py

gcloud config set project lucidex-502504

gcloud run deploy api --source . --region asia-southeast1 --allow-unauthenticated

