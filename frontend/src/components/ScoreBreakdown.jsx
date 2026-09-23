function ComponentScore({ label, data }) {
  const percentage = Number(data?.percentage ?? 0);
  const contribution = Number(data?.contribution ?? 0);
  const weight = Number(data?.weight ?? 0);

  return (
    <div className="score-component">
      <div className="score-component-header">
        <strong>{label}</strong>
        <span>{weight}% weight</span>
      </div>

      <div className="score-component-value">
        {percentage.toFixed(2)}%
      </div>

      <div className="score-progress" aria-hidden="true">
        <span style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }} />
      </div>

      <small>{contribution.toFixed(2)} points contributed</small>
    </div>
  );
}

export default function ScoreBreakdown({ score }) {
  if (!score) return null;

  return (
    <section className="score-panel">
      <div className="final-score">
        <span>Final score</span>
        <strong>{Number(score.final_score ?? 0).toFixed(2)}</strong>
        <small>out of 100</small>
      </div>

      <div className="score-components">
        <ComponentScore label="IO tests" data={score.io} />
        <ComponentScore label="Unit tests" data={score.unit} />
        <ComponentScore label="Static analysis" data={score.static} />
      </div>
    </section>
  );
}
