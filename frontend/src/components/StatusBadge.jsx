export default function StatusBadge({ status }) {
  const normalized = String(status || "unknown").toLowerCase();

  return (
    <span className={`status-badge status-${normalized}`}>
      {normalized}
    </span>
  );
}
