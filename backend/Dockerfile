FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md wsgi.py ./
COPY migrations ./migrations
COPY src ./src

RUN python -m pip install --upgrade pip \
    && pip install -e .

EXPOSE 8000

CMD ["python", "-m", "contester.app"]