# EdTech Autograder - Problem Statement

## 1. Problem Statement

Programming instructors in schools, bootcamps, and other technical learning environments often spend significant time manually reviewing student code. Manual grading becomes increasingly difficult as class sizes grow because instructors must repeatedly execute submissions, compare outputs, inspect implementation details, identify code-quality issues, assign scores, and write feedback.

This creates four core problems:

1. **High grading overhead** - instructors spend substantial time evaluating repetitive programming exercises instead of focusing on teaching and student support.
2. **Inconsistent evaluation** - manual grading can vary between submissions or graders, particularly when several criteria must be considered.
3. **Delayed feedback** - students may wait too long to learn whether their solution is correct or how it can be improved.
4. **Limited scalability** - increasing the number of students or submission attempts increases grading workload proportionally.

The proposed EdTech Autograder addresses this problem by providing a system in which instructors define programming assignments and their evaluation criteria, students submit Python solutions, and the system evaluates those submissions automatically.

Evaluation must support multiple complementary grading methods:

- input/output test cases;
- assert-based unit tests;
- static code analysis; and
- qualitative improvement feedback.

The system must produce deterministic scores from instructor-defined grading rules. AI-generated feedback may provide additional suggestions, but it must not determine or modify a student's score.

Student code must be treated as untrusted input and must not be executed directly inside the application server process.

## 2. Goal

Build a reliable automated grading platform that allows instructors to define structured Python programming assessments and allows students to receive consistent, traceable, and actionable grading results without requiring each submission to be manually evaluated.

## 3. Phase 1 Scope

Phase 1 includes:

- Python programming assignments;
- instructor and student roles;
- assignment creation and publication;
- student `.py` file submission;
- input/output test evaluation;
- assert-based unit-test evaluation;
- static code analysis;
- configurable grading weights and execution limits;
- asynchronous grading;
- submission status tracking;
- deterministic score calculation;
- structured grading feedback; and
- optional AI-assisted improvement suggestions.

## 4. Out of Scope

The following are intentionally excluded from Phase 1:

- languages other than Python;
- SQL grading;
- plagiarism detection;
- real-time proctored examinations;
- LMS integration;
- a custom application-owned sandbox/runtime for executing untrusted code; and
- advanced instructor analytics.
