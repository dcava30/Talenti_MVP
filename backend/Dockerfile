FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.30.0" \
    "sqlalchemy>=2.0.30" \
    "alembic>=1.13.1" \
    "pydantic>=2.8.2" \
    "pydantic-settings>=2.4.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "httpx>=0.27.0" \
    "python-multipart>=0.0.9" \
    "email-validator>=2.1.0" \
    "azure-identity>=1.16.0" \
    "azure-storage-blob>=12.20.0" \
    "azure-communication-identity>=1.3.0" \
    "openai>=1.35.0"

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app

RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
