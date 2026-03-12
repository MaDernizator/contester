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
GET   /api/v1/health
POST  /api/v1/auth/register
POST  /api/v1/auth/login
POST  /api/v1/auth/logout
GET   /api/v1/auth/me
GET   /api/v1/admin/session

GET   /api/v1/admin/contests
POST  /api/v1/admin/contests
GET   /api/v1/admin/contests/<contest_id>
PATCH /api/v1/admin/contests/<contest_id>

GET   /api/v1/admin/contests/<contest_id>/problems
POST  /api/v1/admin/contests/<contest_id>/problems
GET   /api/v1/admin/problems/<problem_id>
PATCH /api/v1/admin/problems/<problem_id>

GET   /api/v1/admin/problems/<problem_id>/test-cases
POST  /api/v1/admin/problems/<problem_id>/test-cases
GET   /api/v1/admin/test-cases/<test_case_id>
PATCH /api/v1/admin/test-cases/<test_case_id>

GET   /api/v1/contests
GET   /api/v1/contests/<slug>
GET   /api/v1/contests/<slug>/problems
GET   /api/v1/contests/<slug>/problems/<problem_code>

POST  /api/v1/contests/<slug>/problems/<problem_code>/submissions
GET   /api/v1/submissions
GET   /api/v1/submissions/<submission_id>
Notes

Participants register via the public API.

Admin accounts are created only via CLI.

Authentication is session-based.

Participants can view only published contests and published problems of published contests.

Source code is sent as JSON field source_code.

The current judge implementation is synchronous and executes Python locally from the backend process.

The runner layer is isolated in a separate module so it can be replaced with Docker-based execution later.

If you run backend locally against Docker PostgreSQL on a custom host port, set DATABASE_URL in backend/.env accordingly.