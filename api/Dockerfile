# Dockerfile for Smart Nurse Call (SNC) Backend API & Cloud Service
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose port for Cloud Run (Cloud Run passes PORT env var, default to 8000)
ENV PORT=8000
EXPOSE 8000

# Start FastAPI application with Uvicorn
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
