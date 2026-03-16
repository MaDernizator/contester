# Contester installation on a clean Windows computer

This guide is the main installation scenario for the first full version of the system.

## What you need

Only one required dependency:

- Docker Desktop

Recommended:

- Windows 10 or Windows 11
- PowerShell

## Step 1. Start Docker Desktop

Install and start Docker Desktop.

After it starts, open PowerShell and check:

```powershell
docker version
docker compose version

Both commands must work.

Step 2. Open the project folder

In PowerShell, go to the repository root.

Example:

cd C:\path\to\contester
Step 3. Run the first-start script
.\scripts\windows\first-run.ps1

What this script does:

checks Docker availability

creates .env from .env.example if needed

generates SECRET_KEY

runs docker compose up --build -d

waits until the system becomes available

prints local and LAN URLs

After that, the system should already be running.

Step 4. Create the first admin
.\scripts\windows\create-admin.ps1

You will be prompted for username and password.

Step 5. Open the UI

Open in browser:

http://127.0.0.1:8080

If you want to use the system from other computers in the same local network, open one of the LAN URLs shown by first-run.ps1.

Step 6. Optional firewall rule for LAN access

If another computer in the same network cannot open the frontend, allow inbound TCP traffic for port 8080:

New-NetFirewallRule `
  -DisplayName "Contester Frontend 8080" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8080
Regular everyday commands

Start the system:

docker compose up -d

Rebuild after code changes:

docker compose up --build -d

Stop the system:

docker compose down

See service status:

docker compose ps

See backend logs:

docker compose logs -f backend

See worker logs:

docker compose logs -f judge-worker
First-run checklist

When installation is finished, check:

frontend opens in browser

login works

admin can create contest

admin can create problem

admin can create test cases

participant can register

participant can submit solution

worker processes the submission

standings update correctly

Troubleshooting
1. docker command not found

Docker Desktop is not installed or not added to PATH.

2. docker compose command not found

Docker Desktop is too old or not started correctly.

3. Frontend does not open on port 8080

Another process may already use port 8080.

Change the port in .env:

FRONTEND_PORT=8090

Then restart:

docker compose up --build -d
4. Backend or worker is unhealthy

Check logs:

docker compose logs -f backend
docker compose logs -f judge-worker
5. Judge does not process submissions

Check worker logs:

docker compose logs -f judge-worker

Also check queue state through admin UI.

6. Another computer cannot access the UI

Check:

you are opening the correct LAN IP

both computers are in the same local network

Windows Firewall allows inbound traffic on the frontend port

Configuration that is usually enough

The default .env values are intended to be enough for a normal local-network deployment on one machine.

The most useful overrides are:

FRONTEND_PORT

SECRET_KEY

WORKER_PROCESSES

Example:

FRONTEND_PORT=8080
WORKER_PROCESSES=4