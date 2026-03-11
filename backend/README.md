# Contester Backend

Backend API for the local contest management system.

## Local development

1. Start PostgreSQL:

```bash
docker compose up -d db

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
Main endpoints
GET  /api/v1/health
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
GET  /api/v1/admin/session
Notes

Participants register via the public API.

Admin accounts are created only via CLI.

Authentication is session-based.

If you run backend locally against Docker PostgreSQL on a custom host port, set DATABASE_URL in backend/.env accordingly.