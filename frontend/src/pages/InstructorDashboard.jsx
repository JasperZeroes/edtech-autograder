import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import {
  listInstructorAssignments,
  publishAssignment,
  unpublishAssignment,
} from "../api/assignments";
import { ApiError } from "../api/client";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../auth/AuthContext";

export default function InstructorDashboard() {
  const { user } = useAuth();
  const location = useLocation();
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [workingId, setWorkingId] = useState(null);

  async function loadAssignments() {
    setLoading(true);
    setError("");

    try {
      const data = await listInstructorAssignments();
      setAssignments(data || []);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to load assignments.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAssignments();
  }, []);

  async function togglePublication(assignment) {
    setWorkingId(assignment.id);
    setError("");

    try {
      if (assignment.status === "published") {
        await unpublishAssignment(assignment.id);
      } else {
        await publishAssignment(assignment.id);
      }
      await loadAssignments();
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to update assignment publication.",
      );
    } finally {
      setWorkingId(null);
    }
  }

  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">Instructor workspace</div>
          <h1>Welcome, {user?.full_name || "Instructor"}</h1>
          <p className="muted">
            Create assessments, publish them for students, and manage the
            grading workflow.
          </p>
        </div>

        <Link className="button button-primary" to="/instructor/assignments/new">
          + Create assignment
        </Link>
      </div>

      {location.state?.flash ? (
        <div className="alert alert-success">{location.state.flash}</div>
      ) : null}

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div className="section-toolbar">
        <div>
          <h2>My assignments</h2>
          <p className="muted">
            Draft assignments remain private until you publish them.
          </p>
        </div>
        <button
          className="button button-ghost"
          disabled={loading}
          onClick={loadAssignments}
          type="button"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="panel centered-panel">
          <div className="loader" aria-label="Loading assignments" />
        </div>
      ) : assignments.length === 0 ? (
        <EmptyState
          title="No assignments yet"
          description="Create your first Python assignment to start the demo workflow."
          action={
            <Link className="button button-primary" to="/instructor/assignments/new">
              Create assignment
            </Link>
          }
        />
      ) : (
        <div className="assignment-grid">
          {assignments.map((assignment) => (
            <article className="assignment-card" key={assignment.id}>
              <div className="assignment-card-top">
                <StatusBadge status={assignment.status} />
                <span className="assignment-id">#{assignment.id}</span>
              </div>

              <h3>{assignment.title}</h3>
              <p>{assignment.description}</p>

              <div className="assignment-meta">
                <span>
                  IO <strong>{assignment.grading_policy?.io_weight ?? 0}%</strong>
                </span>
                <span>
                  Unit{" "}
                  <strong>{assignment.grading_policy?.unit_weight ?? 0}%</strong>
                </span>
                <span>
                  Static{" "}
                  <strong>{assignment.grading_policy?.static_weight ?? 0}%</strong>
                </span>
              </div>

              <div className="card-actions">
                <button
                  className={
                    assignment.status === "published"
                      ? "button button-ghost"
                      : "button button-secondary"
                  }
                  disabled={workingId === assignment.id}
                  onClick={() => togglePublication(assignment)}
                  type="button"
                >
                  {workingId === assignment.id
                    ? "Updating…"
                    : assignment.status === "published"
                      ? "Unpublish"
                      : "Publish"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="demo-note">
        <strong>Next:</strong> Commit 24 adds instructor submission review and
        full result inspection.
      </div>
    </section>
  );
}
