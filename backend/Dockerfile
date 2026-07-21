FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install dependencies using uv
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Create a system user to run the app safely
RUN addgroup --system app && adduser --system --ingroup app app

# Copy src code with correct ownership
COPY --chown=app:app src/ ./src

USER app 

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
