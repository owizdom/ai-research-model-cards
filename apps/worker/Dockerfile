FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*

COPY packages/db /app/packages/db
RUN pip install --no-cache-dir /app/packages/db

COPY apps/worker/pyproject.toml /app/apps/worker/pyproject.toml
COPY apps/worker/src /app/apps/worker/src
WORKDIR /app/apps/worker
RUN pip install --no-cache-dir -e .

# Pre-download model weights
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

CMD ["python", "-m", "src.main"]
