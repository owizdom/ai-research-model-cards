FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY packages/db /app/packages/db
RUN pip install --no-cache-dir /app/packages/db

COPY apps/collector/pyproject.toml /app/apps/collector/pyproject.toml
COPY apps/collector/src /app/apps/collector/src
WORKDIR /app/apps/collector
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "src.scheduler.runner"]
