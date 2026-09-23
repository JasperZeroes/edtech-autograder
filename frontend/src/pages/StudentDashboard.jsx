import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { listPublishedAssignments } from "../api/assignments";
import { ApiError } from "../api/client";
import { listMySubmissions } from "../api/submissions";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../auth/AuthContext";

export default function StudentDashboard() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const [assignmentData, submissionData] = await Promise.all([
        listPublishedAssignments(),
        listMySubmissions(),
      ]);
      setAssignments(assignmentData || []);
      setSubmissions(submissionData || []);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to load the student dashboard.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const latestAttemptByAssignment = useMemo(() => {
    const latest = new Map();

    for (const submission of submissions) {
      const current = latest.get(submission.assignment_id);
      if (!current || submission.attempt_number > current.attempt_number) {
        latest.set(submission.assignment_id, submission);
      }
    }

    return latest;
  }, [submissions]);

  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">Student workspace</div>
          <h1>Welcome, {user?.full_name || "Student"}</h1>
          <p className="muted">
            Browse published assignments, upload Python solutions, and track
            each attempt.
          </p>
        </div>

        <button
          className="button button-ghost"
          disabled={loading}
          onClick={loadDashboard}
          type="button"
        >
          Refresh
        </button>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {loading ? (
        <div className="panel centered-panel">
          <div className="loader" aria-label="Loading student dashboard" />
        </div>
      ) : (
        <>
          <div className="section-toolbar">
            <div>
              <h2>Available assignments</h2>
              <p className="muted">
                Only published, student-safe assignment details appear here.
              </p>
            </div>
          </div>

          {assignments.length === 0 ? (
            <EmptyState
              title="No published assignments"
              description="When an instructor publishes an assignment, it will appear here."
            />
          ) : (
            <div className="assignment-grid">
              {assignments.map((assignment) => {
                const latest = latestAttemptByAssignment.get(assignment.id);

                return (
                  <article className="assignment-card" key={assignment.id}>
                    <div className="assignment-card-top">
                      <span className="status-badge status-published">
                        published
                      </span>
                      <span className="assignment-id">#{assignment.id}</span>
                    </div>

                    <h3>{assignment.title}</h3>
                    <p>{assignment.description}</p>

                    {latest ? (
                      <div className="latest-attempt">
                        <span>Latest attempt #{latest.attempt_number}</span>
                        <StatusBadge status={latest.status} />
                      </div>
                    ) : (
                      <div className="latest-attempt">
                        <span>No attempts yet</span>
                      </div>
                    )}

                    <div className="card-actions">
                      <Link
                        className="button button-primary"
                        to={`/student/assignments/${assignment.id}`}
                      >
                        Open assignment
                      </Link>
                    </div>
                  </article>
                );
              })}
            </div>
          )}

          <div className="section-toolbar section-toolbar-spaced">
            <div>
              <h2>My submissions</h2>
              <p className="muted">
                Every upload creates an independent attempt.
              </p>
            </div>
          </div>

          {submissions.length === 0 ? (
            <EmptyState
              title="No submissions yet"
              description="Open an assignment and upload a .py file to create your first attempt."
            />
          ) : (
            <div className="submission-table-wrap">
              <table className="submission-table">
                <thead>
                  <tr>
                    <th>Submission</th>
                    <th>Assignment</th>
                    <th>Attempt</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {submissions.map((submission) => (
                    <tr key={submission.id}>
                      <td>#{submission.id}</td>
                      <td>#{submission.assignment_id}</td>
                      <td>{submission.attempt_number}</td>
                      <td>
                        <StatusBadge status={submission.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <div className="demo-note">
        <strong>Next:</strong> Commit 24 makes completed attempts clickable and
        shows the full result/AI-feedback experience.
      </div>
    </section>
  );
}
