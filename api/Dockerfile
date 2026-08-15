# Dockerfile for Smart Nurse Call (SNC) Backend API & Cloud Service
# ----------------------------------------------------------------------------
# ⚠️ Build context ต้องเป็น **repo root** (มีทั้ง api/ และ app/) ตาม 5-Core:
#   docker build -f api/Dockerfile -t <tag> .
#   หรือ gcloud builds submit --config api/cloudbuild.yaml <repo-root>
# ----------------------------------------------------------------------------
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code (api/ → /app, server.py อยู่ที่ /app/server.py)
COPY api/ .

# Copy frontend dashboard (app/ → /app/app — server.py อ่าน static_dir = ../app)
COPY app/ app/

# Expose port for Cloud Run (Cloud Run passes PORT env var, default to 8000)
ENV PORT=8000
EXPOSE 8000

# Start FastAPI application with Uvicorn
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
