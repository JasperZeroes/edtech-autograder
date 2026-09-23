import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getPublishedAssignment } from "../api/assignments";
import { ApiError } from "../api/client";
import { submitSolution } from "../api/submissions";
import StatusBadge from "../components/StatusBadge";

export default function StudentAssignment() {
  const { assignmentId } = useParams();
  const [assignment, setAssignment] = useState(null);
  const [file, setFile] = useState(null);
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAssignment() {
      setLoading(true);
      setError("");

      try {
        const data = await getPublishedAssignment(assignmentId);
        setAssignment(data);
      } catch (requestError) {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : "Unable to load the assignment.",
        );
      } finally {
        setLoading(false);
      }
    }

    loadAssignment();
  }, [assignmentId]);

  function selectFile(event) {
    const selected = event.target.files?.[0] || null;
    setSubmission(null);
    setError("");

    if (!selected) {
      setFile(null);
      return;
    }

    if (!selected.name.toLowerCase().endsWith(".py")) {
      setFile(null);
      setError("Please choose a Python .py file.");
      event.target.value = "";
      return;
    }

    setFile(selected);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!file) {
      setError("Choose a .py file before submitting.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const created = await submitSolution(assignmentId, file);
      setSubmission(created);
      setFile(null);

      const input = event.currentTarget.elements.namedItem("solutionFile");
      if (input) input.value = "";
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to submit the solution.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="panel centered-panel">
        <div className="loader" aria-label="Loading assignment" />
      </div>
    );
  }

  if (!assignment) {
    return (
      <section className="panel">
        <h1>Assignment unavailable</h1>
        <p className="muted">{error || "The assignment could not be loaded."}</p>
        <Link className="button button-primary" to="/student">
          Back to dashboard
        </Link>
      </section>
    );
  }

  const visibleExamples = assignment.visible_io_examples || [];
  const visibleUnitTest = assignment.visible_unit_test || null;
  const staticRequirements = assignment.static_requirements || null;

  return (
    <section className="workflow-page">
      <Link className="back-link" to="/student">
        ← Back to assignments
      </Link>

      <div className="assignment-hero">
        <div>
          <div className="eyebrow">Published assignment #{assignment.id}</div>
          <h1>{assignment.title}</h1>
          <p>{assignment.description}</p>
        </div>
        <span className="status-badge status-published">published</span>
      </div>

      {assignment.instructions ? (
        <section className="content-card">
          <h2>Instructions</h2>
          <p className="pre-wrap">{assignment.instructions}</p>
        </section>
      ) : null}

      <div className="student-assignment-grid">
        <div className="assignment-content-column">
          <section className="content-card">
            <div className="content-card-heading">
              <h2>Grading overview</h2>
              <span>Deterministic</span>
            </div>

            <div className="score-policy-grid">
              <div>
                <span>IO</span>
                <strong>{assignment.grading_policy?.io_weight ?? 0}%</strong>
              </div>
              <div>
                <span>Unit</span>
                <strong>{assignment.grading_policy?.unit_weight ?? 0}%</strong>
              </div>
              <div>
                <span>Static</span>
                <strong>{assignment.grading_policy?.static_weight ?? 0}%</strong>
              </div>
            </div>
          </section>

          {visibleExamples.length > 0 ? (
            <section className="content-card">
              <h2>Visible examples</h2>
              <div className="example-list">
                {visibleExamples.map((example, index) => (
                  <div className="example-card" key={`${example.name}-${index}`}>
                    <strong>{example.name}</strong>
                    <div>
                      <span>Input</span>
                      <pre>{example.stdin || "(no stdin)"}</pre>
                    </div>
                    <div>
                      <span>Expected output</span>
                      <pre>{example.expected_stdout}</pre>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {visibleUnitTest ? (
            <section className="content-card">
              <h2>Visible unit test</h2>
              <pre className="code-block">{visibleUnitTest.test_code}</pre>
            </section>
          ) : null}

          {staticRequirements ? (
            <section className="content-card">
              <h2>Static requirements</h2>
              <dl className="requirements-list">
                <div>
                  <dt>Required functions</dt>
                  <dd>
                    {(staticRequirements.required_functions || []).join(", ") ||
                      "None"}
                  </dd>
                </div>
                <div>
                  <dt>Forbidden imports</dt>
                  <dd>
                    {(staticRequirements.forbidden_imports || []).join(", ") ||
                      "None"}
                  </dd>
                </div>
                <div>
                  <dt>Maximum complexity</dt>
                  <dd>
                    {staticRequirements.max_cyclomatic_complexity ?? "Not set"}
                  </dd>
                </div>
              </dl>
            </section>
          ) : null}
        </div>

        <aside className="submission-panel">
          <div className="eyebrow">Submit solution</div>
          <h2>Upload your Python file</h2>
          <p className="muted">
            Each successful upload creates a new independent attempt and is
            queued for asynchronous grading.
          </p>

          {error ? <div className="alert alert-error">{error}</div> : null}

          {submission ? (
            <div className="submission-success">
              <div>
                <strong>Attempt #{submission.attempt_number} created</strong>
                <span>Submission #{submission.id}</span>
              </div>
              <StatusBadge status={submission.status} />
              <p>
                Your solution is durable and queued for grading. Commit 24 adds
                the live result screen.
              </p>
            </div>
          ) : null}

          <form className="upload-form" onSubmit={handleSubmit}>
            <label className="file-drop">
              <span className="file-icon">PY</span>
              <strong>{file ? file.name : "Choose solution.py"}</strong>
              <small>
                {file
                  ? `${Math.max(1, Math.ceil(file.size / 1024))} KB selected`
                  : "Python files only"}
              </small>
              <input
                accept=".py,text/x-python,text/plain"
                name="solutionFile"
                onChange={selectFile}
                type="file"
              />
            </label>

            <button
              className="button button-primary button-block"
              disabled={!file || submitting}
              type="submit"
            >
              {submitting ? "Submitting…" : "Submit for grading"}
            </button>
          </form>
        </aside>
      </div>
    </section>
  );
}
