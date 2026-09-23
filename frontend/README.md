# EdTech Autograder Frontend

Commit 22 provides the authentication/application shell for the backend demo.

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

By default it calls the FastAPI backend at:

```text
http://localhost:8000
```

Change `VITE_API_BASE_URL` in `frontend/.env` if the backend runs elsewhere.

## Commit 22 scope

Implemented:

- landing page
- student/instructor registration
- shared login
- access/refresh token storage
- `/auth/me` session restoration
- role-protected routing
- instructor/student dashboard shells
- logout
- responsive UI
- FastAPI CORS support for the frontend origin

Assignment authoring, student submission, and results are added in the next commits.
