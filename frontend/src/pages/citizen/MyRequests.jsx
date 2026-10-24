import { Link } from "react-router";
import { fetchMySos } from "../../api";
import { SeverityTag, SosStatusTag } from "../../components/Tags";
import { EMERGENCY_TYPES, labelFor } from "../../constants";
import { usePolling } from "../../lib/hooks";
import { formatTime } from "../../lib/time";

function RequestRows({ items }) {
  return (
    <ul className="req-list">
      {items.map((sos) => (
        <li key={sos.id}>
          <Link to={`/sos/${sos.id}`} className="req-row">
            <span className="req-id mono">#{sos.id}</span>
            <span className="req-main">
              <span className="req-title">{sos.emergency_type ? labelFor(EMERGENCY_TYPES, sos.emergency_type) : "Details not sent"}</span>
              <span className="req-meta mono">
                Sent {formatTime(sos.created_at)}
                {sos.people_affected ? ` / ${sos.people_affected} ${sos.people_affected === 1 ? "person" : "people"}` : ""}
              </span>
            </span>
            <span className="req-tags">
              <SosStatusTag status={sos.status} />
              <SeverityTag severity={sos.severity} />
            </span>
            <span className="req-provider mono">{sos.assigned_provider?.organisation_name ?? "No responder yet"}</span>
            <span className="req-go mono" aria-hidden="true">
              &rarr;
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function MyRequests() {
  const mine = usePolling(fetchMySos, 10000);
  const all = mine.data ?? [];
  const active = all.filter((sos) => sos.status !== "RESOLVED");
  const past = all.filter((sos) => sos.status === "RESOLVED");

  return (
    <section className="sec list-page" aria-labelledby="requests-title">
      <p className="sec-bar mono">
        <span>(03) My requests</span>
        <span>{mine.data ? `${all.length} total` : "…"}</span>
      </p>
      <div className="list-head">
        <h1 id="requests-title" className="list-title">
          My requests
        </h1>
        <Link className="btn btn--red btn--lg" to="/sos">
          New SOS &rarr;
        </Link>
      </div>

      {mine.loading && !mine.data && <p className="list-empty mono">Loading…</p>}
      {mine.error && !mine.data && <p className="list-empty mono">Could not load your requests: {mine.error}</p>}
      {mine.data && all.length === 0 && <p className="list-empty mono">You have not sent any SOS requests.</p>}

      {active.length > 0 && (
        <div className="list-group">
          <p className="list-group-title label">Active / {active.length}</p>
          <RequestRows items={active} />
        </div>
      )}
      {past.length > 0 && (
        <div className="list-group">
          <p className="list-group-title label">Resolved / {past.length}</p>
          <RequestRows items={past} />
        </div>
      )}
    </section>
  );
}
