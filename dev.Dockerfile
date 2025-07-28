FROM python:3.11 AS builder

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Non-root user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /uvx /bin/

# Copy dependency management files
COPY ./pyproject.toml \
    ./uv.lock \
    ./

# Install dependencies
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
# To suppress warnings from uv attempting to use hardlinks
ENV UV_LINK_MODE=copy
WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

### RUNTIME ###
# Use multi-stage build in prod
# FROM python:3.11 AS runtime

# Copy venv
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY ./src /app/src/

# Run
# USER appuser
WORKDIR /app/src
CMD ["python", "-m", "main", "--host", "0.0.0.0"]
