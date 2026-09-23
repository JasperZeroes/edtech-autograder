# EdTech Autograder

A backend-first automated grading platform for Python programming assignments.

The system allows instructors to create and publish assignments with deterministic grading rules, and allows students to submit `.py` files for asynchronous grading. Untrusted code is executed outside the application process through Judge0, static-analysis rules are evaluated without executing student code, and the final score is calculated from the instructor's configured weighting policy.

Optional AI-assisted feedback is advisory only: it can explain student-safe grading facts and suggest improvements, but it cannot change the authoritative score.

## Why this project exists

Programming assignments are difficult to grade consistently at scale. A useful autograder must do more than run code: it must protect hidden tests, isolate untrusted execution, preserve a complete grading trail, apply instructor-defined scoring rules correctly, survive infrastructure failures, and enforce role/ownership boundaries.

This project addresses those concerns with explicit domain boundaries and deterministic grading rules.

For the original problem statement and functional analysis, see:

- [`docs/problem-statement.md`](docs/problem-statement.md)
- [`docs/functional-requirements.md`](docs/functional-requirements.md)

For the architecture and domain model, see:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/domain-design.md`](docs/domain-design.md)
- [`docs/architecture-decisions.md`](docs/architecture-decisions.md)

## Core capabilities

### Instructor workflow

An instructor can:

- register and authenticate
- create a draft Python assignment
- configure weighted grading components
- define visible and hidden IO tests
- define a unit-test specification
- define static-analysis rules
- configure execution limits
- publish/unpublish an assignment
- review student attempts
- inspect full grading evidence, including hidden-test diagnostics for assignments they own

### Student workflow

A student can:

- register and authenticate
- discover published assignments
- see only student-safe assignment information
- upload a `.py` solution
- create multiple independent attempts
- poll submission/grading status
- view deterministic score breakdowns
- view visible-test feedback and aggregate hidden-test results
- optionally request AI-assisted improvement suggestions after grading completes

## Architecture

The design follows a layered, domain-oriented architecture:

```text
┌───────────────────────────────────────────────────────────────────────┐
│ Presentation                                                          │
│ FastAPI routers, request/response schemas, authentication dependencies│
└───────────────────────────────┬───────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────┐
│ Application                                                           │
│ Use cases, commands, queries, ports, transaction boundaries           │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────┐
│ Domain                                                                │
│ Identity | Assessment | Submission | Grading                          │
│ Entities, value objects, invariants, deterministic scoring            │
└───────────────────────────────▲───────────────────────────────────────┘
                                │
┌───────────────────────────────┴───────────────────────────────────────┐
│ Infrastructure                                                        │
│ SQLAlchemy/PostgreSQL | Celery/Redis | Judge0 | AST/Radon | OpenAI   │
└───────────────────────────────────────────────────────────────────────┘
```

The domain layer does not depend on FastAPI, SQLAlchemy, Celery, Redis, Judge0, or the AI provider.

Editable diagrams are included in [`docs/diagrams`](docs/diagrams):

- `system-architecture.drawio` / `system-architecture.svg`
- `ddd-context-map.drawio` / `ddd-context-map.svg`
- `data-model-erd.drawio` / `data-model-erd.svg`

## Domain-driven design

The solution is divided into four bounded contexts:

| Context | Responsibility |
| --- | --- |
| Identity | Users, roles, authentication-facing identity rules |
| Assessment | Assignment authoring, grading policy, publication readiness, tests/rules |
| Submission | Student attempts, source-code value object, submission lifecycle |
| Grading | Execution evidence, deterministic scoring, result projection, advisory feedback |

The core grading path is intentionally deterministic:

```text
Assessment grading policy
        +
Evaluation outcomes
        ↓
Normalize component scores
        ↓
Apply configured weights
        ↓
Persist authoritative GradingResult
```

A configured component contributes:

```text
component percentage = earned points / possible points × 100

weighted contribution = component percentage × component weight / 100

final score = IO contribution + Unit contribution + Static contribution
```

For example, with a `70 / 20 / 10` policy:

```text
IO      50% × 70% = 35
Unit   100% × 20% = 20
Static  50% × 10% =  5
                       ──
Final                 60
```

This explicitly avoids a common grading bug where raw component points are simply added even though component weights have been configured.

## Asynchronous grading flow

```text
Student uploads .py file
        ↓
Validate extension / MIME / size / UTF-8
        ↓
Persist QUEUED submission
        ↓
Commit transaction
        ↓
Enqueue submission_id through Celery
        ↓
Redis broker
        ↓
Grading worker
        ↓
QUEUED → RUNNING
        ↓
IO execution through Judge0
Unit-test execution through Judge0
Static analysis through AST + Radon
        ↓
EvaluationOutcome[]
        ↓
Weighted GradingResult
        ↓
Persist result + evidence
        ↓
RUNNING → COMPLETED
```

The submission is committed **before** queue dispatch. If the queue is temporarily unavailable, the student's submitted source remains durable instead of disappearing with the queue failure.

## Security and correctness boundaries

### Untrusted code

Student code is never executed directly inside the FastAPI application process. Dynamic execution is delegated through the `CodeExecutionGateway` abstraction to Judge0.

### Hidden tests

Hidden tests remain available internally for grading and instructor review, but student-facing projections expose only aggregate information such as:

```json
{
  "total": 3,
  "passed": 2,
  "failed_or_other": 1
}
```

Hidden names, inputs, expected outputs, and diagnostics are not included in student result DTOs or AI-feedback requests.

### Infrastructure failure vs student failure

The system distinguishes academic evidence from platform failure:

- student timeout/runtime failure → deterministic grading outcome; grading can complete
- Judge0/service outage → submission is marked failed; no fabricated score is created

### Idempotency

One authoritative grading result is permitted per submission.

A duplicate worker delivery for an already-completed submission returns the existing result rather than grading again. The database reinforces this with a unique constraint on `grading_results.submission_id`.

## AI-assisted feedback

AI feedback is optional and non-authoritative.

The AI receives only the student's safe grading projection:

- final score
- component percentages
- visible evaluation facts
- aggregate hidden-test counts
- deterministic feedback facts

It does **not** receive:

- raw source code
- hidden test names
- hidden inputs
- hidden expected outputs
- hidden diagnostic details

The AI integration has no repository mutation path and cannot update points, weights, outcomes, or the final score.

If no AI provider is configured, the normal grading platform continues to operate; only the optional feedback endpoint is unavailable.

## Technology

- Python 3.10+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Celery
- Redis
- Judge0
- Python `ast`
- Radon
- Argon2
- JWT
- Pytest

## Repository structure

```text
app/
├── application/
│   ├── assessment/
│   ├── grading/
│   ├── identity/
│   └── submission/
├── domain/
│   ├── assessment/
│   ├── grading/
│   ├── identity/
│   └── submission/
├── infrastructure/
│   ├── grading/
│   ├── persistence/
│   ├── queue/
│   └── security/
├── presentation/
│   └── api/
└── workers/

alembic/
docs/
tests/
```

## Local setup

### 1. Create the environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If development dependencies are already installed in the environment, the second command is not required again.

### 2. Configure environment variables

```bash
cp .env.example .env
```

At minimum, configure a PostgreSQL database and a sufficiently long JWT secret.

For asynchronous grading, also configure Redis and Judge0.

AI settings are optional.

### 3. Apply database migrations

```bash
alembic upgrade head
```

The current migration chain is:

```text
0001 create users
→ 0002 create assessment tables
→ 0003 create submissions
→ 0004 create grading results
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

Interactive API documentation is then available through FastAPI's `/docs` endpoint.

### 5. Start Redis

Run a Redis instance reachable through `REDIS_URL`.

### 6. Start the grading worker

```bash
celery -A app.infrastructure.queue.celery_app.celery_app worker --loglevel=info
```

### 7. Run Judge0

Run a Judge0 deployment reachable through `JUDGE0_BASE_URL` and set the configured Python language ID for that deployment.

## Testing

Run the complete suite:

```bash
python -m pytest
```

Run the system-validation suite:

```bash
python -m pytest tests/system -v
```

The test strategy covers:

- domain invariants
- application use cases
- SQLAlchemy repositories/UoWs
- security/token behavior
- Judge0 adapter normalization
- AST/Radon analysis
- Celery dispatch
- API authorization and serialization
- hidden-test confidentiality
- weighted scoring
- multiple attempts
- timeout behavior
- infrastructure failures
- end-to-end workflow validation
- advisory AI isolation

See [`docs/testing-strategy.md`](docs/testing-strategy.md) for details.

## API workflow summary

Representative endpoints include:

```text
Authentication
POST /auth/register
POST /auth/login
POST /auth/refresh
GET  /auth/me

Assessment
POST  /assignments
GET   /assignments/mine
GET   /assignments/{id}/manage
PATCH /assignments/{id}/configuration
POST  /assignments/{id}/publish
POST  /assignments/{id}/unpublish
GET   /assignments
GET   /assignments/{id}

Submission
POST /assignments/{id}/submissions
GET  /submissions/mine
GET  /submissions/{id}

Results
GET /submissions/{id}/result
GET /assignments/{id}/submissions
GET /assignments/{id}/submissions/{submission_id}/result

Optional AI
POST /submissions/{id}/ai-feedback
```

## Design trade-offs and current limitations

This is intentionally a focused backend take-home rather than a production-complete learning management system.

Notable limitations:

- the current unit-test mechanism appends an instructor test specification to student source rather than creating an isolated multi-file pytest workspace
- submission attempt numbering uses repository-level next-attempt calculation plus a database uniqueness constraint; high-contention production systems would add locking/retry or a dedicated sequence strategy
- Celery worker concurrency protection is application-level plus result uniqueness; a production deployment could add stronger row-level claiming/locking
- AI suggestions are generated on demand and are not persisted
- there is no frontend
- operational concerns such as distributed tracing, rate limiting, autoscaling, CI/CD, and production secret management are outside the assignment scope

These choices preserve the important engineering concerns for the exercise: correctness, explicit boundaries, deterministic grading, security, testability, and readable architecture.

## Submission documentation

A concise interviewer-oriented walkthrough is available in:

[`docs/final-submission.md`](docs/final-submission.md)
