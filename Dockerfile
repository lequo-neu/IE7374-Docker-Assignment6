# syntax=docker/dockerfile:1

# Stage 1: install dependencies into a virtual environment and train the model.
# Training here means the model is built with exactly the libraries it will be
# served with, and a model below the accuracy floor stops the build.
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt && pip freeze > /srv/installed-packages.txt
COPY app/ app/
RUN python -m app.train --output-dir /srv/model

# Stage 2: run the test suite inside the same environment that will ship.
# Only built when asked for with --target test.
FROM builder AS test
COPY requirements-dev.txt pytest.ini ./
RUN pip install -r requirements-dev.txt
COPY tests/ tests/
RUN pytest -q

# Stage 3: the image that actually runs. No compilers, no test tools, no root.
FROM python:3.12-slim AS runtime
ARG GIT_SHA=local
LABEL org.opencontainers.image.title="iris-classifier" \
      org.opencontainers.image.description="Iris classifier served with Flask and gunicorn" \
      org.opencontainers.image.source="https://github.com/lequo-neu/IE7374-Docker-Assignment6" \
      org.opencontainers.image.revision="${GIT_SHA}"
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/srv/model \
    GIT_SHA=${GIT_SHA}
WORKDIR /srv
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /srv/model /srv/model
COPY --from=builder /srv/installed-packages.txt /srv/installed-packages.txt
COPY app/ app/
USER app
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "app.main:create_app()"]
