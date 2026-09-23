# EdTech Autograder Frontend

A lightweight React/Vite demo interface over the FastAPI autograder backend.

## Requirements

Vite 8 requires Node.js 20.19+ or 22.12+.

## Run locally

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Backend default:

```text
http://localhost:8000
```

## Implemented demo flow

### Authentication

- student/instructor registration
- login
- session restoration through `/auth/me`
- role-protected routes
- logout

### Instructor

- list own assignments
- create/configure assignments
- grading weights
- visible/hidden IO tests
- optional unit/static grading
- execution limits
- publish/unpublish
- list all submissions for an owned assignment
- inspect queued/running/failed/completed submission state
- view complete deterministic grading evidence
- view hidden evaluation evidence as the assignment owner

### Student

- browse published assignments
- open student-safe assignment details
- upload `.py` files
- create multiple attempts
- view submission history
- open any attempt
- automatically poll queued/running attempts
- view weighted final score
- view IO/unit/static component breakdown
- view visible evaluation evidence
- view aggregate hidden-test results without secret data
- request optional AI improvement suggestions after grading completes

## External-service behavior

The frontend does not require Judge0 to render submission states.

If a submission is still queued/running, the result page polls every 3 seconds.

If grading infrastructure fails, the UI shows the backend failure reason separately from a normal wrong-answer/timeout result.

When Judge0 is correctly configured, completed results automatically render without frontend changes.

AI feedback is also optional. If no AI provider is configured, the authoritative deterministic result remains fully usable and only the AI-suggestion request fails.

## Build

```bash
npm run build
```
