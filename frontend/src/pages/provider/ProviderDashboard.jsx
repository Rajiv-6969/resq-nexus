import { useCallback } from "react";
import { Link } from "react-router";
import { fetchProviderRequests, fetchProviderResources } from "../../api";
import CapacityBar from "../../components/CapacityBar";
import Counters from "../../components/Counters";
import { ResourceGlyph } from "../../components/Glyphs";
import PageLoader from "../../components/PageLoader";
import ProviderGate from "../../components/provider/ProviderGate";
import RequestCard from "../../components/provider/RequestCard";
import { ResourceStatusTag } from "../../components/Tags";
import { RESOURCE_META } from "../../constants";
import { useNow, usePolling } from "../../lib/hooks";
import { useRequestActions } from "../../lib/requestActions";
import { availabilityText } from "../../lib/resources";
import { formatTime } from "../../lib/time";
import { useAuth } from "../../state/contexts";

const NEARBY_KM = 25;
const ORDER = { PENDING: 0, ACKNOWLEDGED: 1, DISPATCHED: 2, RESOLVED: 3 };

function Dashboard() {
  const { user } = useAuth();
  const provider = user.provider;
  const now = useNow(30000);
  const loadBoard = useCallback((options) => fetchProviderRequests(NEARBY_KM, options), []);
  const board = usePolling(loadBoard, 10000);
  const resources = usePolling(fetchProviderResources, 30000);
  const { busyId, act } = useRequestActions(board.refresh);

  if (!board.data && board.loading) return <PageLoader label="Loading your dashboard" />;

  const assigned = board.data?.assigned ?? [];
  const nearby = board.data?.nearby ?? [];
  const open = assigned.filter((s) => s.status !== "RESOLVED").sort((a, b) => ORDER[a.status] - ORDER[b.status]);
  const own = resources.data ?? [];
  const mainType = provider.organisation_type;
  const meta = RESOURCE_META[mainType];
  const capacity = own.filter((r) => r.resource_type === mainType && r.status !== "CLOSED").reduce((sum, r) => sum + r.capacity_available, 0);

  return (
    <div className="dash">
      <section className="sec dash-head" aria-labelledby="dash-title">
        <p className="sec-bar mono">
          <span>(01) Dashboard</span>
          <span>
            Refreshes every 10 s{board.updatedAt ? ` / ${formatTime(board.updatedAt)}` : ""}
          </span>
        </p>
        <div className="dash-title-row">
          <div>
            <p className="sec-no">
              {meta?.org} / {provider.region ?? provider.address ?? "—"}
            </p>
            <h1 id="dash-title" className="list-title">
              {provider.organisation_name}
            </h1>
          </div>
          <span className="tag tag--res is-open tag--lg">Approved</span>
        </div>
        <Counters
          label="Your organisation at a glance"
          items={[
            { label: "Awaiting acceptance", value: open.filter((s) => s.status === "PENDING").length, tone: "red" },
            { label: "In progress", value: open.filter((s) => s.status !== "PENDING").length },
            { label: `Nearby unassigned (${NEARBY_KM} km)`, value: nearby.length, tone: "orange" },
            { label: "Resolved by you", value: assigned.length - open.length },
            { label: "Resources open", value: own.filter((r) => r.status === "OPEN").length, unit: `of ${own.length}` },
            { label: `${meta?.plural ?? "Capacity"} available`, value: capacity, unit: meta?.unit },
          ]}
        />
      </section>

      <div className="dash-grid">
        <section className="dash-col" aria-labelledby="action-title">
          <div className="dash-col-head">
            <h2 id="action-title" className="dash-col-title">
              Needs your action
            </h2>
            <Link to="/provider/requests" className="btn btn--sm">
              Map and all requests &rarr;
            </Link>
          </div>
          {open.length === 0 ? (
            <p className="list-empty mono">Nothing is assigned to your organisation right now.</p>
          ) : (
            <ol className="req-cards">
              {open.map((sos) => (
                <li key={sos.id}>
                  <RequestCard sos={sos} now={now} onAction={act} busy={busyId === sos.id} compact />
                </li>
              ))}
            </ol>
          )}
          <h3 className="dash-sub label">Nearest unassigned / {nearby.length}</h3>
          {nearby.length === 0 ? (
            <p className="list-empty mono">No unassigned requests within {NEARBY_KM} km.</p>
          ) : (
            <ol className="req-cards">
              {nearby.slice(0, 3).map((sos) => (
                <li key={sos.id}>
                  <RequestCard sos={sos} now={now} onAction={act} busy={busyId === sos.id} compact />
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="dash-col dash-col--side" aria-labelledby="res-title">
          <div className="dash-col-head">
            <h2 id="res-title" className="dash-col-title">
              My resources
            </h2>
            <Link to="/provider/resources" className="btn btn--sm">
              Update availability &rarr;
            </Link>
          </div>
          {resources.error && <p className="list-empty mono">Could not load resources: {resources.error}</p>}
          <ul className="mini-res">
            {own.map((r) => (
              <li key={r.id} className={r.status === "CLOSED" ? "is-closed" : ""}>
                <ResourceGlyph type={r.resource_type} status={r.status} size={22} />
                <div className="mini-res-main">
                  <p className="mini-res-name">{r.name}</p>
                  <CapacityBar available={r.capacity_available} total={r.capacity_total} />
                  <p className="mono mini-res-avail">{availabilityText(r)}</p>
                </div>
                <ResourceStatusTag status={r.status} />
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

export default function ProviderDashboard() {
  return (
    <ProviderGate>
      <Dashboard />
    </ProviderGate>
  );
}
