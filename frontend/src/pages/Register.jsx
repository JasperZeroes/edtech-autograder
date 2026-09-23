import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const initialForm = {
  fullName: "",
  email: "",
  password: "",
  role: "student",
};

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await register({
        ...form,
        fullName: form.fullName.trim(),
        email: form.email.trim(),
      });

      navigate("/login", {
        replace: true,
        state: { registered: true },
      });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to create the account. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card auth-card-wide">
        <Link to="/" className="back-link">
          ← Back to home
        </Link>

        <div className="eyebrow">Create your account</div>
        <h1>Register</h1>
        <p className="muted">
          Choose the role you want to demonstrate. Instructor and student
          accounts have separate protected workflows.
        </p>

        {error ? <div className="alert alert-error">{error}</div> : null}

        <form className="form-stack" onSubmit={handleSubmit}>
          <div className="role-choice" role="radiogroup" aria-label="Account role">
            {["student", "instructor"].map((role) => (
              <label
                className={`role-option ${form.role === role ? "selected" : ""}`}
                key={role}
              >
                <input
                  checked={form.role === role}
                  name="role"
                  onChange={updateField}
                  type="radio"
                  value={role}
                />
                <span>
                  <strong>{role === "student" ? "Student" : "Instructor"}</strong>
                  <small>
                    {role === "student"
                      ? "Submit solutions and view results"
                      : "Create assignments and review submissions"}
                  </small>
                </span>
              </label>
            ))}
          </div>

          <label>
            <span>Full name</span>
            <input
              autoComplete="name"
              name="fullName"
              onChange={updateField}
              placeholder="Your name"
              required
              type="text"
              value={form.fullName}
            />
          </label>

          <label>
            <span>Email</span>
            <input
              autoComplete="email"
              name="email"
              onChange={updateField}
              placeholder="you@example.com"
              required
              type="email"
              value={form.email}
            />
          </label>

          <label>
            <span>Password</span>
            <input
              autoComplete="new-password"
              minLength={8}
              name="password"
              onChange={updateField}
              placeholder="At least 8 characters"
              required
              type="password"
              value={form.password}
            />
          </label>

          <button
            className="button button-primary button-block"
            disabled={submitting}
            type="submit"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-switch">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
