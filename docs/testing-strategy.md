# Testing Strategy

The test suite is organized around architectural boundaries rather than only endpoint happy paths.

## Goals

The suite is intended to prove:

1. domain invariants are enforced independently of frameworks
2. use cases coordinate repositories and external ports correctly
3. persistence mappings preserve domain state
4. infrastructure adapters normalize external systems into application contracts
5. API boundaries enforce role, ownership, and confidentiality rules
6. the complete workflow works across bounded contexts

## Test layers

### Domain tests

Domain tests exercise pure business rules without infrastructure.

Examples include:

- email/user invariants
- assignment ownership
- grading policy total equals 100
- assignment publication readiness
- source-code validation
- submission state transitions
- evaluation outcome validation
- weighted score calculation
- deterministic rounding
- hidden-test student projections

These tests are fast and provide the clearest signal when a business rule changes.

### Application tests

Application tests use fakes for repositories, queues, analyzers, and execution gateways.

They verify orchestration such as:

```text
persist submission
→ commit
→ enqueue
```

and:

```text
load submission
→ mark RUNNING
→ evaluate
→ persist result
→ mark COMPLETED
```

They also validate query ownership and student-safe result construction.

### Persistence tests

SQLAlchemy repository tests use an isolated test database setup to verify:

- aggregate round trips
- assignment child mappings
- submission attempts
- grading result snapshots
- child evaluation outcomes
- uniqueness constraints
- unit-of-work behavior

### Infrastructure adapter tests

External services are replaced with protocol-level fakes.

Judge0 adapter tests verify:

- request payload translation
- configured execution limits
- status normalization
- runtime conversion
- malformed-response handling

Static-analysis tests verify:

- required functions
- forbidden imports
- syntax errors
- Radon complexity
- proof that source inspection does not execute student code

Celery queue tests verify task name and submission-ID dispatch.

AI adapter tests verify:

- provider request shape
- API-key behavior
- text extraction
- malformed-response behavior
- safe facts only

### API tests

FastAPI dependencies are overridden with fakes.

The tests validate:

- authentication
- role restrictions
- assignment ownership
- upload validation
- result polling
- instructor review
- student result confidentiality
- queue outage behavior
- optional AI behavior

### System-validation tests

The system suite exercises the complete in-process workflow:

```text
register
→ login
→ create assignment
→ configure
→ publish
→ discover
→ submit
→ queue
→ grade
→ persist
→ student result
→ instructor review
```

It also validates:

- multiple attempts
- student timeout behavior
- Judge0/service failure behavior
- queue durability
- authorization boundaries
- hidden-test leakage prevention

## Important test properties

### Weighted score regression coverage

The suite explicitly verifies that configured grading weights are applied after normalization.

This protects against the original failure mode where configured weights existed but raw component points were simply summed.

### Confidentiality regression coverage

Hidden-test strings are deliberately placed in internal outcomes and then asserted absent from:

- published student assignment views
- student result views
- AI-feedback requests

### Failure-mode coverage

The tests distinguish:

```text
student-caused failure
```

from:

```text
platform/infrastructure failure
```

because those cases must produce different domain outcomes.

### Idempotency coverage

Repeated delivery of an already-completed grading task must not execute the submission twice or create another authoritative result.

## Running tests

Run all tests:

```bash
python -m pytest
```

Run only system validation:

```bash
python -m pytest tests/system -v
```

Run an individual area:

```bash
python -m pytest tests/domain/grading -v
python -m pytest tests/application/grading -v
python -m pytest tests/infrastructure/grading -v
python -m pytest tests/presentation/api -v
```

## What the suite intentionally does not require

The normal automated test suite does not require live external services such as:

- Redis
- Judge0
- OpenAI

Those integrations are tested behind ports and protocol-level fakes.

A production smoke-test environment could add live contract/integration tests for those services without changing the domain tests.
