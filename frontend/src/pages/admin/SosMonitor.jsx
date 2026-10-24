import { useCallback, useMemo, useRef, useState } from "react";
import { Marker } from "react-leaflet";
import { adminSetSosStatus, assignSos, fetchAdminSos, fetchAdminSummary, fetchSuggestions } from "../../api";
import Counters from "../../components/Counters";
import BaseMap, { FitPoints } from "../../components/maps/BaseMap";
import RequestCard from "../../components/provider/RequestCard";
import { EMERGENCY_TYPES, SOS_STATUSES, SOS_STEPS } from "../../constants";
import { useNow, usePolling } from "../../lib/hooks";
import { sosIcon } from "../../lib/markers";
import { formatTime } from "../../lib/time";
import { useToast } from "../../state/contexts";

// Suggest the nearest suitable provider, assign, or close a request.
function AdminControls({ sos, onChanged }) {
  const toast = useToast();
  const [suggestions, setSuggestions] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (task, done) => {
    setBusy(true);
    try {
      const result = await task();
      done?.(result);
    } catch (err) {
      toast.error(`Request #${sos.id}`, err.message);
    } finally {
      setBusy(false);
    }
  };
  const suggest = () => run(() => fetchSuggestions(sos.id), setSuggestions);
  const assign = (provider) =>
    run(
      () => assignSos(sos.id, provider.id),
      () => {
        toast.success(`Request #${sos.id} assigned`, `${provider.organisation_name} has been asked to accept it.`);
        setSuggestions(null);
        onChanged();
      },
    );
  const resolve = () =>
    run(
      () => adminSetSosStatus(sos.id, "RESOLVED"),
      () => {
        toast.success(`Request #${sos.id} closed`, "Marked as resolved.");
        onChanged();
      },
    );

  if (sos.status === "RESOLVED") return null;
  return (
    <div className="admin-controls">
      <p className="mono admin-assigned">
        {sos.assigned_provider ? `Assigned: ${sos.assigned_provider.organisation_name}${sos.status === "PENDING" ? " (waiting to accept)" : ""}` : "Not assigned"}
      </p>
      <div className="admin-buttons">
        {sos.status === "PENDING" && (
          <button type="button" className="btn btn--sm btn--solid" onClick={suggest} disabled={busy}>
            Suggest nearest provider
          </button>
        )}
        <button type="button" className="btn btn--sm" onClick={resolve} disabled={busy}>
          Mark resolved
        </button>
      </div>
      {suggestions && (
        <ol className="suggestions">
          {suggestions.candidates.length === 0 && <li className="mono">No approved provider with free capacity within {suggestions.radius_km} km.</li>}
          {suggestions.candidates.slice(0, 3).map((c) => (
            <li key={`${c.provider.id}-${c.resource.id}`}>
              <span>
                <strong>{c.provider.organisation_name}</strong>
                <span className="mono">
                  {" "}
                  {c.distance_km.toFixed(1)} km / {c.resource.capacity_available} {c.resource.unit} free / covers {c.matched_needs.join(", ")}
                </span>
              </span>
              <button type="button" className="btn btn--sm btn--red" onClick={() => assign(c.provider)} disabled={busy}>
                Assign
              </button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function SosMonitor() {
  const now = useNow(30000);
  const [statuses, setStatuses] = useState(["PENDING", "ACKNOWLEDGED", "DISPATCHED"]);
  const [types, setTypes] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const listRef = useRef(null);
  const filters = useRef({ status: statuses, type: types });

  const loadList = useCallback((options) => fetchAdminSos(filters.current, options), []);
  const list = usePolling(loadList, 10000);
  const summary = usePolling(fetchAdminSummary, 10000);
  const refresh = () => {
    list.refresh();
    summary.refresh();
  };

  const toggle = (value, current, set, key) => {
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    set(next);
    filters.current = { ...filters.current, [key]: next };
    list.refresh();
  };

  const items = useMemo(() => list.data ?? [], [list.data]);
  const points = items.map((s) => [s.latitude, s.longitude]);
  const s = summary.data;

  const select = (id) => {
    setSelectedId(id);
    window.requestAnimationFrame(() => listRef.current?.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  };

  return (
    <section className="sec board" aria-labelledby="monitor-title">
      <p className="sec-bar mono">
        <span>(01) SOS monitor</span>
        <span>Refreshes every 10 s{list.updatedAt ? ` / ${formatTime(list.updatedAt)}` : ""}</span>
      </p>
      <div className="board-head board-head--stack">
        <h1 id="monitor-title" className="list-title">
          SOS monitor
        </h1>
        <Counters
          label="Live summary"
          items={[
            { label: "Active SOS", value: s?.sos.active, tone: "red" },
            { label: "Pending", value: s?.sos.pending, tone: "orange" },
            { label: "Dispatched", value: s?.sos.dispatched },
            { label: "Resolved", value: s?.sos.resolved },
            { label: "Shelter capacity", value: s?.shelter_capacity_available, unit: "places" },
            { label: "Ambulances available", value: s?.ambulances_available },
          ]}
        />
        <div className="monitor-filters">
          <p className="label">Status</p>
          <div className="chips" role="group" aria-label="Filter by status">
            {SOS_STATUSES.map((st) => (
              <button key={st} type="button" className={`chip${statuses.includes(st) ? " is-on" : ""}`} aria-pressed={statuses.includes(st)} onClick={() => toggle(st, statuses, setStatuses, "status")}>
                {SOS_STEPS[st].label}
              </button>
            ))}
          </div>
          <p className="label">Type</p>
          <div className="chips" role="group" aria-label="Filter by emergency type">
            {EMERGENCY_TYPES.map((t) => (
              <button key={t.value} type="button" className={`chip${types.includes(t.value) ? " is-on" : ""}`} aria-pressed={types.includes(t.value)} onClick={() => toggle(t.value, types, setTypes, "type")}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      {list.error && <p className="form-error board-error">Could not refresh: {list.error}</p>}

      <div className="board-body">
        <div className="map-pane board-map">
          <BaseMap center={{ latitude: 20.5, longitude: 79 }} zoom={5} label="Map of SOS requests coloured by severity">
            <FitPoints points={points} fitKey={`${statuses.join()}|${types.join()}|${items.length > 0}`} maxZoom={12} />
            {items.map((x) => (
              <Marker
                key={x.id}
                position={[x.latitude, x.longitude]}
                icon={sosIcon(x.severity?.level, x.status, x.id === selectedId)}
                zIndexOffset={x.id === selectedId ? 1000 : 0}
                title={`#${x.id} ${x.severity?.level ?? "No details"} / ${x.status}`}
                eventHandlers={{ click: () => select(x.id) }}
              />
            ))}
          </BaseMap>
          <div className="map-legend mono" aria-label="Severity colours">
            <span className="lg lg--critical">Critical</span>
            <span className="lg lg--high">High</span>
            <span className="lg lg--medium">Medium</span>
            <span className="lg lg--low">Low</span>
            <span className="lg lg--none">No details</span>
          </div>
        </div>
        <div className="board-list" ref={listRef}>
          <p className="res-count mono">{items.length} requests / active and most severe first</p>
          {items.length === 0 && <p className="list-empty mono">No requests match these filters.</p>}
          <ol className="req-cards">
            {items.map((sos) => (
              <li key={sos.id}>
                <RequestCard sos={sos} now={now} selected={sos.id === selectedId} onSelect={setSelectedId} extra={<AdminControls sos={sos} onChanged={refresh} />} />
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
