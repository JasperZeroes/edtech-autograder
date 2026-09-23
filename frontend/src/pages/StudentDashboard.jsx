import { useAuth } from "../auth/AuthContext";

export default function StudentDashboard() {
  const { user } = useAuth();

  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">Student workspace</div>
          <h1>Welcome, {user?.full_name || "Student"}</h1>
          <p className="muted">
            Published assignments, uploads, attempts, and results will appear
            here.
          </p>
        </div>
        <span className="status-chip status-chip-neutral">Authenticated</span>
      </div>

      <div className="dashboard-grid">
        <article className="dashboard-card">
          <span className="card-number">01</span>
          <h2>Available assignments</h2>
          <p>
            Browse instructor-published assessments without exposing hidden
            grading cases.
          </p>
          <button className="button button-primary" disabled type="button">
            Available in Commit 23
          </button>
        </article>

        <article className="dashboard-card">
          <span className="card-number">02</span>
          <h2>Your results</h2>
          <p>
            Track grading status and see the deterministic component score
            breakdown.
          </p>
          <button className="button button-secondary" disabled type="button">
            Available in Commit 24
          </button>
        </article>
      </div>

      <div className="demo-note">
        <strong>Commit 22 scope:</strong> authentication and role-protected
        application shell are live. Submission workflows are added next.
      </div>
    </section>
  );
}
