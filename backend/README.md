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
GET   /api/v1/contests/<slug>/standings

POST  /api/v1/contests/<slug>/problems/<problem_code>/submissions
GET   /api/v1/submissions
GET   /api/v1/submissions/<submission_id>
Judge backends

Two execution backends are supported:

local — default, executes Python/C++ directly from the backend process.

docker — runs Python/C++ inside an isolated Docker container.

Enable Docker judge backend

Build the judge image from the repository root:

docker build -t contester-judge:local -f infra/judge/Dockerfile infra/judge

In backend/.env, enable Docker backend:

JUDGE_EXECUTION_BACKEND=docker
JUDGE_DOCKER_BINARY=docker
JUDGE_DOCKER_IMAGE=contester-judge:local

Restart backend.

Notes

Participants register via the public API.

Admin accounts are created only via CLI.

Authentication is session-based.

Participants can view only published contests and published problems of published contests.

Source code is sent as JSON field source_code.

Supported submission languages: python, cpp.

The runner layer is isolated in separate modules so it can be swapped between local and Docker execution backends.

Docker backend is intended primarily for host-based backend execution. If backend itself runs inside a container, Docker CLI/socket access must be configured separately.

For C++ support, a compiler such as g++ must be available in PATH, or CXX_COMPILER must point to it explicitly when using the local backend.

Standings are calculated in ICPC-like style using contest starts_at as the reference point. If starts_at is absent, contest created_at is used as a fallback.

If you run backend locally against Docker PostgreSQL on a custom host port, set DATABASE_URL in backend/.env accordingly.