FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*

# Node 22 + Claude Code CLI — needed by src/extractor/claude_cli.py because the
# Anthropic Messages API rejects sk-ant-oat01 OAuth tokens (anthropics/claude-code#37205).
# The CLI picks up CLAUDE_CODE_OAUTH_TOKEN from env and routes through Max sub.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g @anthropic-ai/claude-code && \
    claude --version && \
    rm -rf /var/lib/apt/lists/*

# Onboarding stub — claude CLI tries an interactive theme picker on first run
# without this (Anthropic GitHub issue #8938).
RUN mkdir -p /root/.claude && \
    echo '{"hasCompletedOnboarding": true}' > /root/.claude.json && \
    chmod 600 /root/.claude.json

# Install CPU-only PyTorch first (saves ~1.5GB vs full torch)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY data /app/data
COPY packages/db /app/packages/db
RUN pip install --no-cache-dir /app/packages/db

COPY apps/worker/pyproject.toml /app/apps/worker/pyproject.toml
COPY apps/worker/src /app/apps/worker/src
COPY scripts /app/scripts
WORKDIR /app/apps/worker
RUN pip install --no-cache-dir -e . && rm -rf /root/.cache

# Model downloads at runtime to keep image small
CMD ["python", "-m", "src.main"]
