import { SOS_STEPS } from "../constants";

// Small mono tags for SOS status, severity and resource status.
export function SosStatusTag({ status, size }) {
  return <span className={`tag tag--sos is-${status.toLowerCase()}${size === "lg" ? " tag--lg" : ""}`}>{SOS_STEPS[status]?.label ?? status}</span>;
}

export function SeverityTag({ severity, showScore = false, size }) {
  if (!severity) return <span className={`tag tag--nodetail${size === "lg" ? " tag--lg" : ""}`}>No details yet</span>;
  return (
    <span className={`tag ${severity.level.toLowerCase()}${size === "lg" ? " tag--lg" : ""}`} title={`Severity score ${severity.score.toFixed(2)}`}>
      {severity.level}
      {showScore && <span className="tag-score">{severity.score.toFixed(2)}</span>}
    </span>
  );
}

export function ResourceStatusTag({ status }) {
  return <span className={`tag tag--res is-${status.toLowerCase()}`}>{status}</span>;
}
