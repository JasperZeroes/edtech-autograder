# Architecture Decisions

This document summarizes the most important architectural decisions in the EdTech Autograder and the reasoning behind them.

## 1. Use domain boundaries instead of framework-first organization

### Decision

Separate the system into the bounded contexts:

- Identity
- Assessment
- Submission
- Grading

and keep domain rules independent of FastAPI, SQLAlchemy, Celery, Redis, Judge0, and the AI provider.

### Why

The most important rules in the project are business rules rather than framework rules:

- who owns an assignment
- when an assignment is ready to publish
- which grading components are required
- how a submission moves through its lifecycle
- how points are normalized and weighted
- which grading evidence a student may see

Keeping those rules in the domain makes them testable without HTTP, databases, workers, or external services.

### Consequence

Infrastructure can be replaced behind ports without changing grading rules.

---

## 2. Treat the database schema and domain model as different concerns

### Decision

Map SQLAlchemy persistence models to explicit domain objects instead of using ORM entities as the domain.

### Why

Database constraints defend persisted state, but they do not replace domain behavior.

For example:

```text
database
UNIQUE(submission_id)

domain/application
completed submissions reuse their existing result
```

Both are useful, but they solve different problems.

### Consequence

Repositories perform mapping between persistence and domain representations.

---

## 3. Make grading deterministic and authoritative before introducing AI

### Decision

The authoritative score is calculated entirely from deterministic evaluation outcomes and the instructor's grading policy.

AI is advisory only.

### Why

Academic scoring must be reproducible and auditable. A model-generated mark would introduce non-determinism and make it difficult to explain why the same submission received a particular score.

The deterministic path is:

```text
EvaluationOutcome[]
        ↓
component earned / possible
        ↓
component percentage
        ↓
configured component weight
        ↓
weighted contribution
        ↓
final score
```

### Consequence

The AI integration has no capability to change the score.

---

## 4. Normalize component scores before applying weights

### Decision

For each component:

```text
percentage = earned / possible × 100
contribution = percentage × weight / 100
```

The final score is the sum of the weighted contributions.

### Why

The original reference implementation stored component weights but added raw component points directly. That means the configured policy did not actually control the final grade.

The new calculation makes the policy authoritative.

### Consequence

A component carrying a positive weight must have evaluated possible points. Otherwise grading fails rather than silently producing a misleading score.

---

## 5. Persist a submission before queue dispatch

### Decision

The submission API commits the `QUEUED` submission before attempting to enqueue the grading task.

### Why

If queue dispatch fails before persistence, the student's source can be lost.

The chosen ordering is:

```text
save submission
→ commit
→ enqueue submission_id
```

not:

```text
enqueue
→ save
```

### Consequence

A queue outage can produce a `503`, but the student's attempt remains durable and can be retried operationally.

---

## 6. Execute untrusted code outside the application server

### Decision

Student code is executed only through a `CodeExecutionGateway` implemented by the Judge0 adapter.

### Why

Running arbitrary student code inside the FastAPI or worker process would create unnecessary security and reliability risk.

### Consequence

The application consumes normalized execution results rather than Judge0-specific status codes.

---

## 7. Separate student-code failure from platform failure

### Decision

Student failures become grading evidence; infrastructure failures do not.

Examples:

```text
student infinite loop
→ TIMEOUT outcome
→ zero points for that evaluation
→ grading may still complete
```

```text
Judge0 unavailable
→ CodeExecutionUnavailableError
→ submission FAILED
→ no fabricated grading result
```

### Why

Students should not lose academic points because infrastructure is unavailable.

---

## 8. Protect hidden tests at the projection boundary

### Decision

Keep complete grading evidence internally, but create separate student-facing and instructor-facing result projections.

### Why

Deleting or manually stripping hidden fields in each API handler is error-prone.

The safer model is:

```text
internal GradingResult
        ├── instructor projection → complete evidence
        └── student projection    → visible detail + hidden aggregates
```

### Consequence

Student APIs and AI-feedback requests cannot accidentally serialize hidden test names, inputs, expected outputs, or diagnostics because those fields are not present in the student projection.

---

## 9. Make grading idempotent

### Decision

If a task is delivered again after a submission is completed, return the stored result rather than regrading it.

The database also enforces one result per submission.

### Why

Distributed task systems may deliver tasks more than once.

### Consequence

Idempotency is protected at both the application and persistence layers.

---

## 10. Use static analysis without executing source

### Decision

Use Python `ast` for structural checks and Radon for cyclomatic complexity.

### Why

Required-function checks, forbidden-import checks, syntax validation, and complexity measurement do not require executing student code.

### Consequence

Static analysis stays deterministic and avoids unnecessary sandbox calls.

---

## 11. Keep AI feedback optional and on demand

### Decision

AI feedback is generated only after grading completes and only when a student explicitly requests it.

### Why

The core grading system should not depend on an external AI provider for correctness or availability.

### Consequence

If the provider is unconfigured or unavailable:

- grading still works
- stored results remain unchanged
- only the optional feedback endpoint is unavailable

---

## 12. Treat grading text supplied to AI as untrusted data

### Decision

Provider instructions explicitly tell the model to treat grading facts and diagnostic text as data rather than instructions.

### Why

Some visible diagnostic text may originate from student-controlled execution output.

### Consequence

This reduces the risk that model-facing grading text is interpreted as a prompt instruction.

---

## 13. Keep the take-home focused

### Decision

Do not add a frontend, deployment platform, observability stack, or production-scale infrastructure beyond what is required to demonstrate the backend design.

### Why

The assignment is primarily about problem definition, architecture, functional analysis, DDD, tests, and code quality.

### Consequence

The project spends complexity budget on the core engineering risks:

- domain correctness
- isolation
- deterministic grading
- async processing
- access control
- persistence
- testing
