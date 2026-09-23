import { Link } from "react-router-dom";

export default function Home() {
  return (
    <main className="landing">
      <section className="landing-panel">
        <div className="eyebrow">Backend demo interface</div>
        <h1>Grade Python assignments with a clear student and instructor workflow.</h1>
        <p>
          A lightweight interface for the EdTech Autograder backend. Instructors
          create assessments and review results. Students submit Python solutions
          and track grading outcomes.
        </p>

        <div className="landing-actions">
          <Link className="button button-primary" to="/register">
            Create account
          </Link>
          <Link className="button button-secondary" to="/login">
            Sign in
          </Link>
        </div>

        <div className="feature-strip">
          <div>
            <strong>Instructor</strong>
            <span>Create and publish assignments</span>
          </div>
          <div>
            <strong>Student</strong>
            <span>Upload Python solutions</span>
          </div>
          <div>
            <strong>Results</strong>
            <span>Track deterministic grading</span>
          </div>
        </div>
      </section>
    </main>
  );
}
