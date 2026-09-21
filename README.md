# EdTech Autograder API

Backend service for an automated programming assessment platform.

## Initial scaffold

This first version contains only a minimal FastAPI application and a health endpoint. Domain features, persistence, authentication, grading, and background processing will be introduced incrementally in later commits.

## Requirements

- Python 3.10.10

## Setup

```bash
python -m venv .venv
```

Activate the virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Verify the service:

```text
GET http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```
