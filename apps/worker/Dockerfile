FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (saves ~1.5GB vs full torch)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY packages/db /app/packages/db
RUN pip install --no-cache-dir /app/packages/db

COPY apps/worker/pyproject.toml /app/apps/worker/pyproject.toml
COPY apps/worker/src /app/apps/worker/src
WORKDIR /app/apps/worker
RUN pip install --no-cache-dir -e . && rm -rf /root/.cache

# Model downloads at runtime to keep image small
CMD ["python", "-m", "src.main"]
