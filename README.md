# Contester

Local-network contest management system with:

- frontend
- backend API
- PostgreSQL
- asynchronous judge worker
- isolated judge sandbox containers

## One-command deployment

Requirements:

- Docker Desktop

Start the whole system from the repository root:

```powershell
docker compose up --build -d

After startup, the web UI is available at:

http://127.0.0.1:8080

From another computer in the same local network, open:

http://YOUR_HOST_IP:8080
First admin

Create the first admin account:

docker compose exec backend flask --app wsgi create-admin
Stop the system
docker compose down
Rebuild after code changes
docker compose up --build -d
Runtime architecture

The main long-lived services are:

db

backend

judge-worker

frontend

judge-base

judge-base exists so the dedicated sandbox image is built and available in the same docker compose up --build.

When a submission is judged:

backend stores it as pending

judge-worker claims it

judge-worker launches a short-lived isolated sandbox container from contester-judge:local

sandbox executes Python or C++ with resource limits

sandbox container is removed after execution

Multi-worker model

judge-worker can now run multiple worker processes inside one container.

Default:

WORKER_PROCESSES=2

Override example:

$env:WORKER_PROCESSES="4"
docker compose up --build -d

This is useful on machines with several CPU cores.

Isolation model

Sandbox containers are launched with:

no network

read-only root filesystem

writable tmpfs for /tmp

dropped Linux capabilities

no-new-privileges

CPU, memory and PID limits

separate shared workspace volume only for submission files

Useful environment overrides

You can override these variables before startup:

FRONTEND_PORT — default 8080

SECRET_KEY

POSTGRES_DB

POSTGRES_USER

POSTGRES_PASSWORD

WEB_CONCURRENCY

CPP_COMPILE_TIMEOUT_SEC

JUDGE_POLL_INTERVAL_SEC

JUDGE_RUNNING_SUBMISSION_TIMEOUT_SEC

WORKER_PROCESSES

Example:

$env:FRONTEND_PORT="8090"
$env:SECRET_KEY="replace-with-a-long-random-value"
$env:WORKER_PROCESSES="4"
docker compose up --build -d
Quick checks

Health through frontend proxy:

Invoke-RestMethod `
  -Method GET `
  -Uri "http://127.0.0.1:8080/api/v1/health"

Create admin:

docker compose exec backend flask --app wsgi create-admin

Show running services:

docker compose ps

Show worker logs:

docker compose logs -f judge-worker
Notes

Frontend and API work from the same origin through nginx proxy.

Backend is not exposed directly to the host by default.

Worker is separate from backend.

Execution does not happen inside the worker container itself in the production compose profile.

Worker requires Docker socket access because it orchestrates short-lived sandbox containers.

Multi-worker parallelism is controlled by WORKER_PROCESSES.

The next infrastructure step is the final clean-machine installation guide and first-run workflow.