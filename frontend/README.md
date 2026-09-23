# EdTech Autograder Frontend

The frontend is a lightweight React/Vite interface over the existing FastAPI backend.

## Requirements

Vite 8 requires Node.js 20.19+ or 22.12+.

## Run locally

From the repository root:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

By default it calls:

```text
http://localhost:8000
```

Change `VITE_API_BASE_URL` in `frontend/.env` if needed.

## Current features

### Authentication

- register as student or instructor
- shared login
- persisted authenticated session through `/auth/me`
- role-protected routes
- logout

### Instructor

- view own assignments
- create a draft assignment
- configure grading weights
- configure visible/hidden IO tests
- optionally configure unit tests
- optionally configure static-analysis rules
- configure runtime/memory limits
- publish immediately or keep as draft
- publish/unpublish existing assignments

### Student

- browse published assignments
- view student-safe assignment details
- view visible IO examples
- view visible unit tests/static requirements when available
- upload `.py` solutions
- create multiple attempts
- view submission history and queued/running/completed/failed state

Result detail, instructor submission review, and AI suggestions are added in Commit 24.

## Build check

```bash
npm run build
```
