ARG PYTHON_VERSION=3.13-slim

# ===== Stage 1: Builder =====
FROM python:${PYTHON_VERSION} AS builder

ARG POETRY_VERSION=2.1.2
ARG POETRY_PLUGIN_EXPORT_VERSION=1.9.0
ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Install dependencies for Poetry and build process
RUN apt-get update && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | POETRY_VERSION=$POETRY_VERSION python3 - \
    && rm -rf /var/lib/apt/lists/*
RUN poetry self add poetry-plugin-export==${POETRY_PLUGIN_EXPORT_VERSION}

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements.txt (no dev deps)
RUN poetry export --without-hashes --only main -f requirements.txt > requirements.txt

# Create and install dependencies into a virtualenv
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# ===== Stage 2: Final image =====
FROM python:${PYTHON_VERSION}

WORKDIR /app

# Copy virtualenv and source code from builder
COPY --from=builder /venv /venv
COPY . .

# Install the CLI tool
RUN /venv/bin/pip install --no-cache-dir .

# Create a non-root user and group and use it
RUN groupadd -g 1001 lgtm && \
    useradd -m -u 1001 -g lgtm -s /bin/bash lgtm
USER lgtm



ENTRYPOINT ["/venv/bin/lgtm"]
