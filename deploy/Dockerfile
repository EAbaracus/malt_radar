# Malt Radar backend image.
# Build context = repository root (so it can COPY backend/).
# Single uvicorn worker: SQLite is single-writer; one process avoids lock storms.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/

# Writable scratch for runtime artifacts; data lives on a mounted volume.
RUN mkdir -p /app/data

EXPOSE 8080

# --no-server-header suppresses the uvicorn banner (fingerprint hardening);
# access log stays on for ops.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-server-header"]
