FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        g++ \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && docker --version \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md wsgi.py ./
COPY migrations ./migrations
COPY src ./src
COPY docker ./docker

RUN python -m pip install --upgrade pip \
    && pip install -e . "gunicorn>=23.0,<24.0" \
    && sed -i 's/\r$//' /app/docker/entrypoint-web.sh /app/docker/entrypoint-worker.sh \
    && useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/.runtime \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/entrypoint-web.sh /app/docker/entrypoint-worker.sh

USER appuser

EXPOSE 8000

CMD ["/app/docker/entrypoint-web.sh"]
