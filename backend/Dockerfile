FROM python:3.12-slim

WORKDIR /app

# System dep for the healthcheck curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The trained model bundle must exist before the container starts - it's
# baked into the image here (see ../ml/README or run `python ml/src/train.py`
# and ensure backend/models/content_performance_bundle.joblib exists before
# building this image).
RUN mkdir -p models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production: no --reload, multiple workers. Tune --workers to your CPU count.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
