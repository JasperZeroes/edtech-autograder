# EdTech Autograder - Functional Analysis

## 1. Actors

The system has two primary actors.

### Instructor

An instructor creates and manages programming assignments, defines how submissions will be evaluated, publishes assignments, and reviews student submissions and results.

### Student

A student views published assignments, submits Python source files, tracks the grading state of a submission, and views the resulting score and feedback.

---

## 2. Core Functional Areas

The Phase 1 system is divided into five functional areas:

1. Identity and access
2. Assignment management
3. Submission management
4. Automated grading
5. Results and feedback

---

## 3. Identity and Access

### FR-01 - User Registration

The system shall allow a user to register with:

- email address;
- password;
- full name; and
- role.

Supported roles in Phase 1 are:

- `instructor`;
- `student`.

### FR-02 - Authentication

The system shall allow registered users to authenticate using their credentials.

### FR-03 - Role-Based Access

The system shall restrict instructor operations to instructors and student operations to students.

A student shall not be able to perform instructor-only assignment-management operations.

---

## 4. Assignment Management

### FR-04 - Create Assignment

An instructor shall be able to create a Python programming assignment containing, at minimum:

- title;
- description;
- instructions;
- programming language;
- grading-weight configuration;
- maximum execution time; and
- maximum memory allowance.

An assignment shall initially be capable of remaining unpublished while the instructor configures its grading rules.

### FR-05 - Edit Assignment

The instructor who owns an assignment shall be able to update its configurable details.

### FR-06 - Configure Input/Output Tests

An instructor shall be able to define one or more input/output test cases for an assignment.

An input/output test case may contain:

- name;
- standard input;
- expected standard output;
- points;
- visibility state; and
- execution order.

The grading process shall compare the student's actual output against the expected output.

### FR-07 - Configure Unit Tests

An instructor shall be able to define assert-based unit-test specifications for an assignment.

The system shall use these tests to validate the behaviour of the student's submitted solution.

### FR-08 - Configure Static Analysis Rules

An instructor shall be able to define static-analysis requirements including supported rules such as:

- required functions;
- forbidden imports; and
- maximum cyclomatic complexity.

Static-analysis rules may contribute points to the final grade.

### FR-09 - Configure Grading Weights

An instructor shall be able to define the percentage contribution of:

- input/output evaluation;
- unit-test evaluation; and
- static analysis.

The grading-weight configuration shall represent a complete grading distribution and therefore total 100 percent.

### FR-10 - Publish Assignment

An instructor shall be able to publish an assignment after its grading configuration is ready for student use.

### FR-11 - Unpublish Assignment

An instructor shall be able to remove an assignment from the set of assignments available to students without deleting the assignment.

### FR-12 - Student Assignment Discovery

A student shall be able to list assignments that are currently published.

### FR-13 - Student Assignment Detail

A student shall be able to view the details of a published assignment required to prepare a submission.

Students shall not receive instructor-only or hidden grading data when viewing an assignment.

---

## 5. Submission Management

### FR-14 - Submit Python Solution

A student shall be able to upload a Python `.py` file for a published assignment.

The submission shall be persisted before grading begins so that the grading process is traceable and recoverable.

### FR-15 - Validate Submission File

The system shall reject submissions that do not meet the supported file constraints for Phase 1.

At minimum, the submitted solution must be a Python source file and must comply with configured upload limits.

### FR-16 - Track Submission State

A submission shall expose its current processing state.

Supported lifecycle states shall include:

- `queued`;
- `running`;
- `completed`; and
- `failed`.

### FR-17 - Multiple Attempts

The data model and grading workflow shall support more than one submission attempt for the same student and assignment.

Each submission attempt shall remain independently traceable.

---

## 6. Automated Grading

### FR-18 - Asynchronous Grading

Grading shall occur outside the request that accepts the student's upload.

Submitting code shall not require the student to keep an HTTP request open while code execution and evaluation complete.

### FR-19 - Safe Code Execution

Student source code shall be treated as untrusted.

The application shall delegate dynamic code execution to a sandboxed execution environment rather than executing submitted code directly in the API process.

Execution shall respect assignment-level resource constraints such as time and memory limits.

### FR-20 - Input/Output Evaluation

For every configured input/output test case, the grading process shall:

1. execute the submitted program using the configured input;
2. obtain the resulting output;
3. compare actual output with expected output; and
4. record whether the test passed or failed.

### FR-21 - Unit-Test Evaluation

The grading process shall execute configured assert-based tests against the submitted solution and record the outcome.

### FR-22 - Static Analysis

The grading process shall inspect submitted Python source without relying only on runtime behaviour.

Supported Phase 1 analysis includes structural checks and complexity-related rules defined by the instructor.

### FR-23 - Score Calculation

The system shall calculate separate grading components for:

- input/output tests;
- unit tests; and
- static analysis.

The final score shall be calculated deterministically according to the assignment's configured grading policy.

The same submission evaluated against the same assignment configuration shall produce the same deterministic score.

### FR-24 - Failure Handling

A grading run shall handle execution failures such as:

- syntax errors;
- runtime errors;
- failed assertions;
- execution timeouts; and
- grading infrastructure failures.

A failure shall not cause the student's submission record to disappear or become untraceable.

### FR-25 - Persist Grading Results

The system shall persist the grading outcome associated with a submission, including the information required to reconstruct the student's result.

---

## 7. Results and Feedback

### FR-26 - View Submission Result

A student shall be able to retrieve the grading result for their own submission after grading has completed.

The result shall contain, where applicable:

- total score;
- grading-component breakdown;
- pass/fail information;
- static-analysis feedback; and
- feedback summary.

### FR-27 - Protect Hidden Tests

If a grading test is marked as hidden, student-facing responses shall not expose confidential test details such as hidden inputs, expected outputs, or instructor test code.

The student may receive enough information to understand that a test failed without receiving the protected test definition.

### FR-28 - Instructor Result Review

An instructor shall be able to review submissions and grading outcomes associated with assignments they own.

### FR-29 - Deterministic Feedback

The system shall generate structured feedback from grading outcomes such as failed tests, execution errors, and static-analysis findings.

### FR-30 - AI-Assisted Feedback

When AI feedback is enabled, the system may generate additional improvement suggestions based on grading results and source-code context.

AI-generated feedback shall be advisory only and shall not alter:

- test outcomes;
- deterministic grading rules; or
- the final score.

---

## 8. Core Business Rules

The following rules define important behaviour that later domain modelling and tests must enforce.

### BR-01 - Assignment Ownership

Only the instructor who owns an assignment may modify its grading configuration.

### BR-02 - Published Assignment Visibility

Students may discover and view only assignments that are published.

### BR-03 - Submission Eligibility

A student may submit a solution only to an assignment that is available for student submissions.

### BR-04 - Complete Grading Distribution

The IO, unit-test, and static-analysis grading weights must total 100 percent.

### BR-05 - Score Determinism

AI-generated content must never influence the numeric score.

### BR-06 - Hidden-Test Confidentiality

Hidden grading configuration must not be exposed through student-facing assignment or result responses.

### BR-07 - Traceable Submission Lifecycle

Every accepted submission must have a persisted identity and processing state before grading execution begins.

### BR-08 - Untrusted Code Isolation

Student code must never be dynamically executed inside the API server process.

### BR-09 - Result Ownership

Students may retrieve results only for submissions they own.

### BR-10 - Historical Attempts

Creating a new submission attempt must not overwrite previous submission attempts or their grading results.

---

## 9. Primary Use Cases

### UC-01 - Instructor Creates and Publishes an Assignment

**Primary actor:** Instructor

**Preconditions:**

- the instructor is authenticated.

**Main flow:**

1. Instructor creates an assignment.
2. Instructor defines IO tests.
3. Instructor defines unit tests.
4. Instructor defines static-analysis rules.
5. Instructor configures grading weights and execution limits.
6. Instructor publishes the assignment.
7. The assignment becomes available to students.

**Postcondition:**

- a valid published assignment is available for student submissions.

### UC-02 - Student Submits a Solution

**Primary actor:** Student

**Preconditions:**

- the student is authenticated;
- the assignment is published; and
- the uploaded file satisfies submission constraints.

**Main flow:**

1. Student selects a published assignment.
2. Student uploads a Python solution.
3. System persists the submission.
4. System marks the submission as queued.
5. System schedules grading.
6. Student receives the submission identifier and current state.

**Postcondition:**

- the submission exists independently of whether grading has already completed.

### UC-03 - System Grades a Submission

**Primary actor:** System

**Preconditions:**

- a valid submission is queued;
- its assignment has grading configuration.

**Main flow:**

1. System marks the grading work as running.
2. Student code is executed in the sandboxed execution environment where dynamic execution is required.
3. IO tests are evaluated.
4. Unit tests are evaluated.
5. Static-analysis rules are evaluated.
6. Component scores are calculated.
7. Final deterministic score is calculated.
8. Structured feedback is generated.
9. Optional AI improvement suggestions are generated.
10. Results are persisted.
11. Submission processing completes successfully or records failure information.

**Postcondition:**

- the grading outcome is traceable to the submitted solution and assignment configuration.

### UC-04 - Student Reviews a Result

**Primary actor:** Student

**Preconditions:**

- the student owns the submission.

**Main flow:**

1. Student requests the submission state or result.
2. System verifies ownership.
3. System returns the permitted result data.
4. Hidden grading configuration remains protected.

**Postcondition:**

- the student can understand their score and relevant improvement feedback without receiving protected instructor test data.

---

## 10. Important Edge Cases

The implementation and test strategy must account for at least the following scenarios:

- a student attempts to submit to an unpublished assignment;
- a student uploads a non-Python file;
- a submission contains invalid Python syntax;
- submitted code raises a runtime exception;
- submitted code exceeds the execution time limit;
- submitted code exceeds supported execution constraints;
- one or more IO tests fail while others pass;
- unit tests fail;
- required functions are missing;
- forbidden imports are present;
- cyclomatic complexity exceeds the configured threshold;
- grading weights do not total 100 percent;
- a student attempts to access another student's submission;
- a student-facing result contains a hidden test failure;
- the external execution service fails or becomes temporarily unavailable;
- AI feedback generation fails after deterministic grading succeeds; and
- a student creates multiple attempts for the same assignment.

---

## 11. Non-Functional Requirements Relevant to Phase 1

### NFR-01 - Security

Untrusted student code must execute in an isolated environment, and protected grading data must not leak to students.

### NFR-02 - Responsiveness

Long-running grading work must not block the submission API request.

### NFR-03 - Reliability

Submission and grading state must remain traceable when execution or downstream services fail.

### NFR-04 - Consistency

Deterministic grading inputs must produce consistent numeric results.

### NFR-05 - Modularity

The system should permit grading strategies and infrastructure integrations to evolve without requiring unrelated areas of the application to be rewritten.

### NFR-06 - Extensibility

The Phase 1 design should not prevent future support for additional languages, grading strategies, analytics, or execution infrastructure.

---

## 12. Phase 1 Success Criteria

The Phase 1 implementation is considered functionally successful when all of the following can be demonstrated:

1. An instructor can create an assignment and configure its evaluation rules.
2. The instructor can publish the assignment.
3. A student can discover the published assignment and upload a Python solution.
4. The submission is persisted and graded asynchronously.
5. Runtime evaluation occurs outside the API server process.
6. IO tests, unit tests, and static-analysis rules contribute to a deterministic result.
7. The student can retrieve their score and permitted feedback.
8. Hidden grading data remains confidential.
9. Failure scenarios remain traceable rather than silently losing submissions.
10. AI feedback, when enabled, remains advisory and does not affect scoring.

---

## 13. Requirements Traceability Summary

| Functional Area | Requirements |
| --- | --- |
| Identity and access | FR-01 to FR-03 |
| Assignment management | FR-04 to FR-13 |
| Submission management | FR-14 to FR-17 |
| Automated grading | FR-18 to FR-25 |
| Results and feedback | FR-26 to FR-30 |

These requirements define **what** the Phase 1 system must do. Architectural structure, domain boundaries, aggregates, value objects, repositories, and infrastructure choices are intentionally deferred to the next design stage.
