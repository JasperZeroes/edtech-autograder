import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getInstructorResult } from "../api/results";
import { InstructorOutcomeList } from "../components/ResultOutcomes";
import ScoreBreakdown from "../components/ScoreBreakdown";
import StatusBadge from "../components/StatusBadge";

const POLL_INTERVAL_MS = 3000;

export default function InstructorResult() {
  const { assignmentId, submissionId } = useParams();
  const [view, setView] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  const loadResult = useCallback(async () => {
    setError("");

    try {
      const data = await getInstructorResult(assignmentId, submissionId);
      setView(data);
      return data;
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to load the instructor grading result.",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, [assignmentId, submissionId]);

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

  if (loading) {
    return (
      <div className="panel centered-panel">
        <div className="loader" aria-label="Loading instructor result" />
      </div>
    );
  }

  if (!view) {
    return (
      <section className="panel">
        <h1>Result unavailable</h1>
        <p className="muted">{error || "The result could not be loaded."}</p>
        <Link
          className="button button-primary"
          to={`/instructor/assignments/${assignmentId}/submissions`}
        >
          Back to submissions
        </Link>
      </section>
    );
  }

  const status = String(view.status || "").toLowerCase();
  const isPending = status === "queued" || status === "running";
  const isCompleted = status === "completed" && view.result;

  return (
    <section className="workflow-page">
      <Link
        className="back-link"
        to={`/instructor/assignments/${assignmentId}/submissions`}
      >
        ← Back to submissions
      </Link>

      <div className="result-hero">
        <div>
          <div className="eyebrow">
            Student #{view.student_id} · Assignment #{view.assignment_id}
          </div>
          <h1>Submission #{view.submission_id}</h1>
          <p className="muted">Attempt #{view.attempt_number}</p>
        </div>
        <StatusBadge status={view.status} />
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {isPending ? (
        <section className="content-card pending-result-card">
          <div className="loader" aria-hidden="true" />
          <div>
            <h2>
              {status === "queued"
                ? "Waiting for grading"
                : "Grading in progress"}
            </h2>
            <p className="muted">
              This instructor view refreshes automatically every 3 seconds.
            </p>
          </div>
        </section>
      ) : null}

      {status === "failed" ? (
        <section className="content-card failure-card">
          <div className="eyebrow">Infrastructure / workflow state</div>
          <h2>Grading did not complete</h2>
          <p className="muted">
            {view.failure_reason ||
              "The grading workflow could not complete this attempt."}
          </p>
        </section>
      ) : null}

      {isCompleted ? (
        <>
          <ScoreBreakdown score={view.result.score} />

          <section className="content-card">
            <div className="content-card-heading">
              <h2>Complete grading evidence</h2>
              <span>instructor-only</span>
            </div>

            <p className="privacy-note instructor-note">
              Because you own this assignment, this view includes both visible
              and hidden evaluation evidence.
            </p>

            <InstructorOutcomeList outcomes={view.result.outcomes} />
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
              <p className="muted">No additional feedback facts were stored.</p>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}
