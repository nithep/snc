# Dockerfile for Smart Nurse Call (SNC) Backend API & Cloud Service
# ----------------------------------------------------------------------------
# ⚠️ Build context ต้องเป็น **repo root** (มีทั้ง api/ และ app/) ตาม 5-Core:
#   docker build -f api/Dockerfile -t <tag> .
#   หรือ gcloud builds submit --config api/cloudbuild.yaml <repo-root>
#
# Production hardening:
#   - multi-stage: builder มี build-essential, runtime ไม่ต้อง (ลด attack surface/size)
#   - non-root user: container รันเป็น nonroot (กัน root escalation)
#   - HEALTHCHECK ผูกกับ /health
# ----------------------------------------------------------------------------

# ---------- Stage 1: builder (ติดตั้ง dependency ที่ต้อง compile) ----------
FROM python:3.10-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt .
# ติดตั้งลง venv แยก เพื่อ copy เฉพาะที่จำเป็นไป runtime
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: runtime (จิ๋ว ปลอดภัย) ----------
FROM python:3.10-slim AS runtime

WORKDIR /app

# ใช้ venv จาก builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# copy โค้ด backend (api/ → /app) + dashboard (app/ → /app/app) + core/ (repo root → /app/core)
# server.py import core.* — บน Pi ผ่าน _REPO_ROOT, ใน container ผ่าน uvicorn app-dir (cwd=/app)
COPY api/ .
COPY app/ app/
COPY core/ core/

# สร้าง user ไม่ใช่ root + ให้สิทธิ์เขียน /app (SQLite + logs)
RUN useradd --create-home --uid 10001 nonroot \
    && chown -R nonroot:nonroot /app
USER nonroot

ENV PORT=8000
EXPOSE 8000

# Healthcheck ใช้ urllib (ไม่มี curl ใน slim)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python3", "-c", "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:'+__import__('os').getenv('PORT','8000')+'/health',timeout=4); sys.exit(0)"]

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]