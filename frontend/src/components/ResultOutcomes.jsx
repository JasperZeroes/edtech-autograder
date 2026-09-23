import StatusBadge from "./StatusBadge";

export function StudentOutcomeList({ outcomes = [] }) {
  if (outcomes.length === 0) {
    return (
      <p className="muted">
        No visible evaluation details were returned for this submission.
      </p>
    );
  }

  return (
    <div className="outcome-list">
      {outcomes.map((outcome, index) => (
        <article className="outcome-card" key={`${outcome.name}-${index}`}>
          <div className="outcome-heading">
            <div>
              <span className="outcome-component">{outcome.component}</span>
              <strong>{outcome.name}</strong>
            </div>
            <StatusBadge status={outcome.status} />
          </div>

          <div className="outcome-points">
            {outcome.earned_points} / {outcome.possible_points} points
          </div>

          {outcome.detail ? (
            <p className="outcome-detail">{outcome.detail}</p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export function InstructorOutcomeList({ outcomes = [] }) {
  if (outcomes.length === 0) {
    return <p className="muted">No evaluation outcomes were stored.</p>;
  }

  return (
    <div className="outcome-list">
      {outcomes.map((outcome, index) => (
        <article className="outcome-card" key={`${outcome.name}-${index}`}>
          <div className="outcome-heading">
            <div>
              <div className="outcome-label-row">
                <span className="outcome-component">{outcome.component}</span>
                {outcome.is_hidden ? (
                  <span className="hidden-chip">hidden</span>
                ) : (
                  <span className="visible-chip">visible</span>
                )}
              </div>
              <strong>{outcome.name}</strong>
            </div>
            <StatusBadge status={outcome.status} />
          </div>

          <div className="outcome-points">
            {outcome.earned_points} / {outcome.possible_points} points
          </div>

          {outcome.detail ? (
            <pre className="diagnostic-block">{outcome.detail}</pre>
          ) : null}
        </article>
      ))}
    </div>
  );
}
