import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getStudentResult, requestAiFeedback } from "../api/results";
import { StudentOutcomeList } from "../components/ResultOutcomes";
import ScoreBreakdown from "../components/ScoreBreakdown";
import StatusBadge from "../components/StatusBadge";

const POLL_INTERVAL_MS = 3000;

export default function StudentResult() {
  const { submissionId } = useParams();
  const [view, setView] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiFeedback, setAiFeedback] = useState(null);
  const [aiError, setAiError] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const pollRef = useRef(null);

  const loadResult = useCallback(async () => {
    setError("");

    try {
      const data = await getStudentResult(submissionId);
      setView(data);
      return data;
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to load the grading result.",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    let cancelled = false;

    async function start() {
      const data = await loadResult();

      if (
        cancelled ||
        !data ||
        !["queued", "running"].includes(String(data.status).toLowerCase())
      ) {
        return;
      }

      pollRef.current = window.setInterval(async () => {
        const latest = await loadResult();
        const status = String(latest?.status || "").toLowerCase();

        if (!["queued", "running"].includes(status) && pollRef.current) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, POLL_INTERVAL_MS);
    }

    start();

    return () => {
      cancelled = true;
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [loadResult]);

  async function handleAiFeedback() {
    setAiLoading(true);
    setAiError("");

    try {
      const response = await requestAiFeedback(submissionId);
      setAiFeedback(response);
    } catch (requestError) {
      setAiError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to generate AI suggestions.",
      );
    } finally {
      setAiLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="panel centered-panel">
        <div className="loader" aria-label="Loading result" />
      </div>
    );
  }

  if (!view) {
    return (
      <section className="panel">
        <h1>Result unavailable</h1>
        <p className="muted">{error || "The submission result could not be loaded."}</p>
        <Link className="button button-primary" to="/student">
          Back to dashboard
        </Link>
      </section>
    );
  }

  const status = String(view.status || "").toLowerCase();
  const isPending = status === "queued" || status === "running";
  const isCompleted = status === "completed" && view.result;

  return (
    <section className="workflow-page">
      <Link className="back-link" to="/student">
        ← Back to student dashboard
      </Link>

      <div className="result-hero">
        <div>
          <div className="eyebrow">Submission #{view.submission_id}</div>
          <h1>Attempt #{view.attempt_number}</h1>
          <p className="muted">
            Assignment #{view.assignment_id}
          </p>
        </div>
        <StatusBadge status={view.status} />
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {isPending ? (
        <section className="content-card pending-result-card">
          <div className="loader" aria-hidden="true" />
          <div>
            <h2>
              {status === "queued" ? "Waiting for grading" : "Grading in progress"}
            </h2>
            <p className="muted">
              This page refreshes automatically every 3 seconds. You can leave
              and return later without losing the submission.
            </p>
          </div>
        </section>
      ) : null}

      {status === "failed" ? (
        <section className="content-card failure-card">
          <div className="eyebrow">Grading did not complete</div>
          <h2>Submission failed</h2>
          <p className="muted">
            {view.failure_reason || "The grading infrastructure could not complete this attempt."}
          </p>
          <p className="muted">
            This is separate from a wrong answer or timeout. Those are normal
            grading outcomes; this status means the grading workflow itself did
            not finish successfully.
          </p>
        </section>
      ) : null}

      {isCompleted ? (
        <>
          <ScoreBreakdown score={view.result.score} />

          <section className="content-card">
            <div className="content-card-heading">
              <h2>Visible evaluation feedback</h2>
              <span>student-safe</span>
            </div>
            <StudentOutcomeList outcomes={view.result.visible_outcomes} />
          </section>

          <section className="content-card">
            <div className="content-card-heading">
              <h2>Hidden-test summary</h2>
              <span>aggregate only</span>
            </div>

            <div className="hidden-summary-grid">
              <div>
                <span>Total hidden</span>
                <strong>{view.result.hidden_summary?.total ?? 0}</strong>
              </div>
              <div>
                <span>Passed</span>
                <strong>{view.result.hidden_summary?.passed ?? 0}</strong>
              </div>
              <div>
                <span>Failed / other</span>
                <strong>{view.result.hidden_summary?.failed_or_other ?? 0}</strong>
              </div>
            </div>

            <p className="privacy-note">
              Hidden test names, inputs, expected outputs, and diagnostics are
              intentionally not exposed to students.
            </p>
          </section>

          <section className="content-card">
            <h2>Deterministic feedback facts</h2>
            {view.result.feedback_facts?.length ? (
              <ul className="feedback-list">
                {view.result.feedback_facts.map((fact, index) => (
                  <li key={`${fact.kind}-${index}`}>
                    <span>{fact.kind}</span>
                    {fact.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No additional feedback facts were generated.</p>
            )}
          </section>

          <section className="content-card ai-feedback-card">
            <div>
              <div className="eyebrow">Optional assistance</div>
              <h2>AI improvement suggestions</h2>
              <p className="muted">
                Suggestions are generated from student-safe grading facts only.
                They do not change your authoritative score.
              </p>
            </div>

            {aiError ? <div className="alert alert-error">{aiError}</div> : null}

            {aiFeedback ? (
              <div className="ai-suggestion">
                <p className="pre-wrap">{aiFeedback.suggestion}</p>
                <small>{aiFeedback.advisory}</small>
              </div>
            ) : (
              <button
                className="button button-secondary"
                disabled={aiLoading}
                onClick={handleAiFeedback}
                type="button"
              >
                {aiLoading ? "Generating suggestions…" : "Get AI suggestions"}
              </button>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}
