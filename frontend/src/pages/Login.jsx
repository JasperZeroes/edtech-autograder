import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const registrationMessage = location.state?.registered
    ? "Registration complete. Sign in with your new account."
    : "";

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
      await login(form.email.trim(), form.password);
      const destination = location.state?.from || "/dashboard";
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link to="/" className="back-link">
          ← Back to home
        </Link>

        <div className="eyebrow">Welcome back</div>
        <h1>Sign in</h1>
        <p className="muted">
          Students and instructors use the same login form. Your role determines
          the dashboard you see.
        </p>

        {registrationMessage ? (
          <div className="alert alert-success">{registrationMessage}</div>
        ) : null}

        {error ? <div className="alert alert-error">{error}</div> : null}

        <form className="form-stack" onSubmit={handleSubmit}>
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
              autoComplete="current-password"
              minLength={8}
              name="password"
              onChange={updateField}
              placeholder="Enter your password"
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
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="auth-switch">
          Need an account? <Link to="/register">Register here</Link>
        </p>
      </section>
    </main>
  );
}
