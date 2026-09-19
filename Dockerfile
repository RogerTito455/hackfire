# HackFire as one service: the FastAPI backend also serves the built dashboard.
# It sits at the repo root because the build needs frontend/, backend/ and data/, and because
# Railway only auto-detects a Dockerfile at the root.
# See docs/setup/deployment.md.

# --- Dashboard -----------------------------------------------------------------
FROM node:24-slim AS dashboard
WORKDIR /repo
# pnpm at the version pinned in package.json's packageManager field.
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/
RUN pnpm install --frozen-lockfile
COPY frontend frontend
RUN pnpm build

# --- API -----------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.11-python3.12-trixie-slim
WORKDIR /repo/backend
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/repo/backend/.venv/bin:$PATH" \
    HACKFIRE_DASHBOARD_DIR=/repo/frontend/dist
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev
COPY backend/app app
COPY data /repo/data
COPY --from=dashboard /repo/frontend/dist /repo/frontend/dist

# One process, one worker: the triage state lives in this process's memory. Railway sets PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
