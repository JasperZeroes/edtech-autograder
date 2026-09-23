import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function InstructorDashboard() {
  const { user } = useAuth();

  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">Instructor workspace</div>
          <h1>Welcome, {user?.full_name || "Instructor"}</h1>
          <p className="muted">
            Your assignment authoring and student-review tools will live here.
          </p>
        </div>
        <span className="status-chip status-chip-neutral">Authenticated</span>
      </div>

      <div className="dashboard-grid">
        <article className="dashboard-card">
          <span className="card-number">01</span>
          <h2>Create assignments</h2>
          <p>
            Build grading policies, IO tests, unit tests, static rules, and
            execution limits.
          </p>
          <button className="button button-primary" disabled type="button">
            Available in Commit 23
          </button>
        </article>

        <article className="dashboard-card">
          <span className="card-number">02</span>
          <h2>Review submissions</h2>
          <p>
            Inspect attempts, grading status, score breakdowns, and full
            instructor evidence.
          </p>
          <button className="button button-secondary" disabled type="button">
            Available in Commit 24
          </button>
        </article>
      </div>

      <div className="demo-note">
        <strong>Commit 22 scope:</strong> authentication and role-protected
        application shell are live. Assignment workflows are added next.
      </div>
    </section>
  );
}
