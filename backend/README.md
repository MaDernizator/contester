# Contester Backend

Backend API for the local contest management system.

## Local development

```bash
python -m pip install -e ".[dev]"
pytest
python -m contester.app

Health check
GET /api/v1/health
