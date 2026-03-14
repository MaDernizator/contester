FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash judge \
    && mkdir -p /judge /judge-shared /tmp \
    && chown -R judge:judge /judge /judge-shared /tmp

WORKDIR /judge
USER judge
