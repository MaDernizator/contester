FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md wsgi.py ./
COPY migrations ./migrations
COPY src ./src
COPY docker ./docker

RUN python -m pip install --upgrade pip \
    && pip install -e . \
    && sed -i 's/\r$//' /app/docker/entrypoint-web.sh /app/docker/entrypoint-worker.sh \
    && useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/.runtime \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/entrypoint-web.sh /app/docker/entrypoint-worker.sh

USER appuser

EXPOSE 8000

CMD ["/app/docker/entrypoint-web.sh"]