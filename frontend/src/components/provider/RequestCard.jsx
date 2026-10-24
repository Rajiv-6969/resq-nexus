import { EMERGENCY_TYPES, INJURY_LEVELS, NEEDS, VULNERABLE_GROUPS, labelFor } from "../../constants";
import { formatTime, timeAgo } from "../../lib/time";
import { AsteriskMark } from "../icons";
import { SeverityTag, SosStatusTag } from "../Tags";

// The next step a provider can take on a request.
const NEXT_ACTION = {
  PENDING: { action: "accept", label: "Accept request" },
  ACKNOWLEDGED: { action: "DISPATCHED", label: "Mark dispatched" },
  DISPATCHED: { action: "RESOLVED", label: "Mark resolved" },
};

const telHref = (phone) => `tel:${phone.replace(/[^+\d]/g, "")}`;

// One SOS request as a provider (or admin) sees it, with its next action.
export default function RequestCard({ sos, now, selected, onSelect, onAction, busy, compact = false, extra }) {
  const next = NEXT_ACTION[sos.status];
  const people = sos.people_affected;
  return (
    <article className={`req-card${selected ? " is-selected" : ""}${sos.status === "RESOLVED" ? " is-resolved" : ""}`} data-id={sos.id}>
      {onSelect && <button type="button" className="req-card-hit" onClick={() => onSelect(sos.id)} aria-label={`Show request ${sos.id} on the map`} />}
      <div className="req-card-head">
        <span className="mono req-card-id">#{sos.id}</span>
        <SosStatusTag status={sos.status} />
        <SeverityTag severity={sos.severity} showScore />
        {sos.distance_km != null && <span className="mono req-card-dist">{sos.distance_km.toFixed(1)} km</span>}
      </div>
      <h3 className="req-card-title">
        {sos.emergency_type ? labelFor(EMERGENCY_TYPES, sos.emergency_type) : "Details not sent yet"}
        {people ? <span className="mono"> / {people} {people === 1 ? "person" : "people"}</span> : null}
      </h3>
      {sos.details_submitted && (
        <ul className="req-card-facts mono">
          <li>Injuries: {labelFor(INJURY_LEVELS, sos.injuries)}</li>
          <li>Needs: {sos.needs.map((n) => labelFor(NEEDS, n)).join(", ")}</li>
          {sos.vulnerable.length > 0 && <li>Vulnerable: {sos.vulnerable.map((v) => labelFor(VULNERABLE_GROUPS, v)).join(", ")}</li>}
        </ul>
      )}
      {!compact && sos.description && <p className="req-card-desc">“{sos.description}”</p>}
      <p className="req-card-meta mono">
        <span title={new Date(sos.created_at).toLocaleString("en-IN")}>
          Sent {formatTime(sos.created_at)} / {timeAgo(sos.created_at, now)}
        </span>
        {sos.citizen && <span>{sos.citizen.full_name}</span>}
        {(sos.contact_phone || sos.citizen?.phone) && (
          <a href={telHref(sos.contact_phone || sos.citizen.phone)}>{sos.contact_phone || sos.citizen.phone}</a>
        )}
      </p>
      {extra}
      {onAction && next && (
        <div className="req-card-actions">
          <button
            type="button"
            className={`btn ${sos.status === "PENDING" ? "btn--red" : "btn--solid"}`}
            onClick={() => onAction(sos, next.action)}
            disabled={busy}
          >
            {busy && <AsteriskMark size={14} className="asterisk loader" />}
            {next.label}
          </button>
        </div>
      )}
    </article>
  );
}
