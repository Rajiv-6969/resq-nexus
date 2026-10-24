import { RESOURCE_META, SOS_STATUSES, SOS_STEPS } from "../../constants";
import { formatTime } from "../../lib/time";

// PENDING → ACKNOWLEDGED → DISPATCHED → RESOLVED, with the time each step was reached.
export function StatusTracker({ sos, compact = false }) {
  const reached = Object.fromEntries(sos.timeline.map((step) => [step.status, step.at]));
  const current = SOS_STATUSES.indexOf(sos.status);
  return (
    <ol className={`tracker${compact ? " tracker--compact" : ""}`} aria-label="Request status">
      {SOS_STATUSES.map((status, i) => {
        const state = i < current ? "done" : i === current ? "current" : "todo";
        return (
          <li key={status} className={`tracker-step is-${state}`} aria-current={state === "current" ? "step" : undefined}>
            <span className="tracker-mark" aria-hidden="true">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="tracker-text">
              <span className="tracker-label">{SOS_STEPS[status].label}</span>
              {!compact && <span className="tracker-detail">{SOS_STEPS[status].detail}</span>}
            </span>
            <span className="tracker-time mono">{reached[status] ? formatTime(reached[status]) : state === "todo" ? "—" : ""}</span>
          </li>
        );
      })}
    </ol>
  );
}

// Who is responding: the assigned organisation with a call link.
export function AssignedProvider({ sos, emptyText = "No responder assigned yet. Admins see your request on the SOS monitor." }) {
  const provider = sos.assigned_provider;
  if (!provider) return <p className="assigned assigned--none mono">{emptyText}</p>;
  return (
    <div className="assigned">
      <p className="label">Assigned responder</p>
      <p className="assigned-name">{provider.organisation_name}</p>
      <p className="assigned-meta mono">
        <span>{RESOURCE_META[provider.organisation_type]?.org ?? provider.organisation_type}</span>
        {sos.assigned_at && <span>Assigned {formatTime(sos.assigned_at)}</span>}
      </p>
      {provider.phone && (
        <a className="btn btn--sm assigned-call" href={`tel:${provider.phone.replace(/[^+\d]/g, "")}`}>
          Call {provider.phone}
        </a>
      )}
    </div>
  );
}
