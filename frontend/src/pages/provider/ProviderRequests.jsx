import { useCallback, useMemo, useRef, useState } from "react";
import { Circle, Marker } from "react-leaflet";
import { fetchProviderRequests } from "../../api";
import BaseMap, { FitPoints } from "../../components/maps/BaseMap";
import PageLoader from "../../components/PageLoader";
import ProviderGate from "../../components/provider/ProviderGate";
import RequestCard from "../../components/provider/RequestCard";
import { usePolling, useNow } from "../../lib/hooks";
import { toValidLatLng } from "../../lib/map";
import { baseIcon, sosIcon } from "../../lib/markers";
import { useRequestActions } from "../../lib/requestActions";
import { formatTime } from "../../lib/time";
import { useAuth } from "../../state/contexts";

const RADII = [10, 25, 50, 100];
const BLACK = "#0A0A0A";

function RequestBoard() {
  const { user } = useAuth();
  const provider = user.provider;
  const [radiusKm, setRadiusKm] = useState(25);
  const [tab, setTab] = useState("assigned");
  const [selectedId, setSelectedId] = useState(null);
  const [showResolved, setShowResolved] = useState(false);
  const listRef = useRef(null);
  const now = useNow(30000);

  const radiusRef = useRef(radiusKm); // read by the poller; updated together with the state
  const load = useCallback((options) => fetchProviderRequests(radiusRef.current, options), []);
  const board = usePolling(load, 10000);
  const { busyId, act } = useRequestActions(board.refresh);

  const assigned = useMemo(() => (board.data?.assigned ?? []).filter((s) => showResolved || s.status !== "RESOLVED"), [board.data, showResolved]);
  const nearby = useMemo(() => board.data?.nearby ?? [], [board.data]);
  const items = tab === "assigned" ? assigned : nearby;
  const resolvedCount = (board.data?.assigned ?? []).filter((s) => s.status === "RESOLVED").length;

  const changeRadius = (km) => {
    setRadiusKm(km);
    radiusRef.current = km;
    board.refresh();
  };
  const select = (id, fromMap = false) => {
    setSelectedId(id);
    if (!fromMap) return;
    const inAssigned = assigned.some((s) => s.id === id);
    setTab(inAssigned ? "assigned" : "nearby");
    window.requestAnimationFrame(() => listRef.current?.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  };

  const home = toValidLatLng([provider.latitude, provider.longitude]) ?? [12.9716, 77.5946];
  const mapItems = [...assigned, ...nearby];
  const points = [home, ...mapItems.map((s) => toValidLatLng(s))].filter(Boolean);

  if (!board.data && board.loading) return <PageLoader label="Loading requests" />;

  return (
    <section className="sec board" aria-labelledby="board-title">
      <p className="sec-bar mono">
        <span>(02) Requests</span>
        <span>
          {provider.organisation_name} / refreshes every 10 s{board.updatedAt ? ` / ${formatTime(board.updatedAt)}` : ""}
        </span>
      </p>
      <div className="board-head">
        <h1 id="board-title" className="list-title">
          Requests
        </h1>
        <div className="board-controls">
          <p className="label">Nearby within</p>
          <div className="chips" role="radiogroup" aria-label="Radius for nearby requests">
            {RADII.map((km) => (
              <button key={km} type="button" role="radio" aria-checked={radiusKm === km} className={`chip${radiusKm === km ? " is-on" : ""}`} onClick={() => changeRadius(km)}>
                {km} km
              </button>
            ))}
          </div>
        </div>
      </div>
      {board.error && <p className="form-error board-error">Could not refresh: {board.error}</p>}

      <div className="board-body">
        <div className="map-pane board-map">
          <BaseMap center={home} zoom={11} label="Map of assigned and nearby requests">
            <FitPoints points={points} fitKey={`${radiusKm}:${mapItems.length > 0}`} maxZoom={13} />
            <Circle center={home} radius={radiusKm * 1000} pathOptions={{ color: BLACK, weight: 1.5, dashArray: "6 6", fill: false, interactive: false }} />
            <Marker position={home} icon={baseIcon(provider.organisation_type)} keyboard={false} title={provider.organisation_name} zIndexOffset={500} />
            {mapItems.map((s) => {
              const pos = toValidLatLng(s);
              if (!pos) return null;
              return (
                <Marker
                  key={s.id}
                  position={pos}
                  icon={sosIcon(s.severity?.level, s.status, s.id === selectedId)}
                  zIndexOffset={s.id === selectedId ? 1000 : 0}
                  title={`#${s.id} ${s.severity?.level ?? "No details"} / ${s.status}`}
                  eventHandlers={{ click: () => select(s.id, true) }}
                />
              );
            })}
          </BaseMap>
          <p className="map-corner map-corner--tl mono">Framed square: your base / squares: requests by severity</p>
        </div>

        <div className="board-list" ref={listRef}>
          <div className="tabs" role="tablist" aria-label="Request lists">
            <button type="button" role="tab" aria-selected={tab === "assigned"} className={`tab${tab === "assigned" ? " is-on" : ""}`} onClick={() => setTab("assigned")}>
              Assigned to us <span className="mono">{assigned.length}</span>
            </button>
            <button type="button" role="tab" aria-selected={tab === "nearby"} className={`tab${tab === "nearby" ? " is-on" : ""}`} onClick={() => setTab("nearby")}>
              Nearby unassigned <span className="mono">{nearby.length}</span>
            </button>
          </div>
          {tab === "assigned" && resolvedCount > 0 && (
            <label className="board-toggle mono">
              <input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} /> Show resolved ({resolvedCount})
            </label>
          )}
          {items.length === 0 ? (
            <p className="list-empty mono">
              {tab === "assigned" ? "Nothing assigned to your organisation right now." : `No unassigned requests within ${radiusKm} km.`}
            </p>
          ) : (
            <ol className="req-cards" role="tabpanel">
              {items.map((sos) => (
                <li key={sos.id}>
                  <RequestCard sos={sos} now={now} selected={sos.id === selectedId} onSelect={select} onAction={act} busy={busyId === sos.id} />
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}

export default function ProviderRequests() {
  return (
    <ProviderGate>
      <RequestBoard />
    </ProviderGate>
  );
}
