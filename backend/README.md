# Contester Backend

Backend API for the local contest management system.

## Local development

1. Start PostgreSQL:

```bash
docker compose up -d db

Create local env file from the example and make sure the DB port is 55432.

Install dependencies:

cd backend
python -m pip install -e ".[dev]"

Apply migrations:

flask --app wsgi db upgrade

Run tests:

pytest

Start the application:

python -m contester.app
Create first admin
flask --app wsgi create-admin
Health check
GET /api/v1/health