import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getInstructorSubmissions } from "../api/results";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";

export default function InstructorSubmissions() {
  const { assignmentId } = useParams();
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadSubmissions = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getInstructorSubmissions(assignmentId);
      setSubmissions(data || []);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to load assignment submissions.",
      );
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    loadSubmissions();
  }, [loadSubmissions]);

  return (
    <section className="workflow-page">
      <Link className="back-link" to="/instructor">
        ← Back to instructor dashboard
      </Link>

      <div className="page-heading">
        <div>
          <div className="eyebrow">Instructor review</div>
          <h1>Assignment #{assignmentId} submissions</h1>
          <p className="muted">
            Review every student attempt and open completed grading evidence.
          </p>
        </div>

        <button
          className="button button-ghost"
          disabled={loading}
          onClick={loadSubmissions}
          type="button"
        >
          Refresh
        </button>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {loading ? (
        <div className="panel centered-panel">
          <div className="loader" aria-label="Loading submissions" />
        </div>
      ) : submissions.length === 0 ? (
        <EmptyState
          title="No student submissions yet"
          description="Attempts for this assignment will appear here as students upload solutions."
        />
      ) : (
        <div className="submission-table-wrap">
          <table className="submission-table">
            <thead>
              <tr>
                <th>Submission</th>
                <th>Student</th>
                <th>Attempt</th>
                <th>Status</th>
                <th>Final score</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {submissions.map((submission) => (
                <tr key={submission.submission_id}>
                  <td>#{submission.submission_id}</td>
                  <td>#{submission.student_id}</td>
                  <td>{submission.attempt_number}</td>
                  <td>
                    <StatusBadge status={submission.status} />
                  </td>
                  <td>
                    {submission.final_score === null ||
                    submission.final_score === undefined
                      ? "—"
                      : Number(submission.final_score).toFixed(2)}
                  </td>
                  <td className="table-action">
                    <Link
                      className="text-link"
                      to={`/instructor/assignments/${assignmentId}/submissions/${submission.submission_id}`}
                    >
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
