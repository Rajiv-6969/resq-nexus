import { useCallback, useEffect, useRef, useState } from "react";
import { Marker } from "react-leaflet";
import { Link, useLocation, useParams } from "react-router";
import { fetchSos } from "../../api";
import BaseMap, { FitPoints } from "../../components/maps/BaseMap";
import PageLoader from "../../components/PageLoader";
import PrototypeNotice from "../../components/sos/PrototypeNotice";
import SosDetailsForm from "../../components/sos/SosDetailsForm";
import { AssignedProvider, StatusTracker } from "../../components/sos/StatusTracker";
import { SeverityTag, SosStatusTag } from "../../components/Tags";
import { EMERGENCY_TYPES, INJURY_LEVELS, NEEDS, SOS_STEPS, VULNERABLE_GROUPS, labelFor } from "../../constants";
import { usePolling } from "../../lib/hooks";
import { baseIcon, sosIcon } from "../../lib/markers";
import { formatTime } from "../../lib/time";
import { useToast } from "../../state/contexts";

const POLL_MS = 10000;
const list = (options, values) => (values.length ? values.map((v) => labelFor(options, v)).join(", ") : "None");

function DetailsSummary({ sos, onEdit }) {
  const rows = [
    ["Emergency type", labelFor(EMERGENCY_TYPES, sos.emergency_type)],
    ["People affected", sos.people_affected],
    ["Injuries", labelFor(INJURY_LEVELS, sos.injuries)],
    ["Needs", list(NEEDS, sos.needs)],
    ["Vulnerable people", list(VULNERABLE_GROUPS, sos.vulnerable)],
    ["Description", sos.description || "—"],
    ["Contact phone", sos.contact_phone],
  ];
  return (
    <div className="details-summary">
      <div className="details-head">
        <h2 className="sos-form-title">Emergency details</h2>
        {onEdit && (
          <button type="button" className="btn btn--sm" onClick={onEdit}>
            Edit details
          </button>
        )}
      </div>
      <dl className="details-list">
        {rows.map(([term, value]) => (
          <div key={term}>
            <dt className="label">{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mono details-note">Sent {formatTime(sos.details_submitted_at)}</p>
    </div>
  );
}

export default function SosTrack() {
  const { id } = useParams();
  const { state } = useLocation();
  const toast = useToast();
  const [stopped, setStopped] = useState(false); // stop polling once resolved
  const [editing, setEditing] = useState(false);
  const [later, setLater] = useState(false);

  const load = useCallback((signal) => fetchSos(id, { signal }), [id]);
  const poll = usePolling(load, stopped ? 0 : POLL_MS);
  const sos = poll.data;
  if (sos?.status === "RESOLVED" && !stopped) setStopped(true);

  // Announce status changes picked up by polling.
  const lastStatus = useRef(null);
  useEffect(() => {
    if (!sos) return;
    const before = lastStatus.current;
    lastStatus.current = sos.status;
    if (before && before !== sos.status) {
      const who = sos.assigned_provider ? ` / ${sos.assigned_provider.organisation_name}` : "";
      toast.info(`Status: ${SOS_STEPS[sos.status].label}`, `${SOS_STEPS[sos.status].detail}${who}`);
    }
  }, [sos, toast]);

  if (!sos) {
    if (poll.error) {
      return (
        <section className="sec empty-page">
          <p className="sec-bar mono">
            <span>(02) Request #{id}</span>
            <span>Not available</span>
          </p>
          <div className="empty-page-body">
            <h1 className="list-title">{poll.error}</h1>
            <Link className="btn btn--lg" to="/requests">
              My requests &rarr;
            </Link>
          </div>
        </section>
      );
    }
    return <PageLoader label="Loading your request" />;
  }

  const resolved = sos.status === "RESOLVED";
  const showForm = !resolved && (editing || (!sos.details_submitted && !later));
  const saved = (updated) => {
    poll.replace(updated);
    setEditing(false);
    toast.success("Details sent", "Responders can now see what you need.");
  };

  const points = [[sos.latitude, sos.longitude]];
  if (sos.assigned_provider) points.push([sos.assigned_provider.latitude, sos.assigned_provider.longitude]);

  return (
    <div className="sos-page">
      <section className="sec track" aria-labelledby="track-title">
        <p className="sec-bar mono">
          <span>(02) Request #{sos.id}</span>
          <span>{stopped ? "Closed" : `Refreshes every 10 s / ${poll.updatedAt ? formatTime(poll.updatedAt) : "…"}`}</span>
        </p>

        {state?.justSent && !resolved && (
          <div className="sent-banner" role="status">
            <span className="sent-banner-mark" aria-hidden="true" />
            <p>
              <strong>Alert sent.</strong> Saved with your location at {formatTime(sos.created_at)}.{" "}
              {sos.details_submitted ? "Your details have been received." : "Add the details below so responders know what to bring."}
            </p>
          </div>
        )}

        <div className="track-head">
          <h1 id="track-title" className="track-title">
            {sos.emergency_type ? labelFor(EMERGENCY_TYPES, sos.emergency_type) : "SOS"} <span className="mono">#{sos.id}</span>
          </h1>
          <div className="track-tags">
            <SosStatusTag status={sos.status} size="lg" />
            <SeverityTag severity={sos.severity} size="lg" />
          </div>
        </div>

        <div className={`track-grid${showForm ? "" : " track-grid--status-first"}`}>
          <div className="track-main">
            {showForm ? (
              <SosDetailsForm sos={sos} onSaved={saved} onCancel={() => (sos.details_submitted ? setEditing(false) : setLater(true))} />
            ) : sos.details_submitted ? (
              <DetailsSummary sos={sos} onEdit={resolved ? null : () => setEditing(true)} />
            ) : (
              <div className="details-missing">
                <p>{resolved ? "No details were sent for this request." : "Responders only have your location so far."}</p>
                {!resolved && (
                  <button type="button" className="btn btn--solid btn--lg" onClick={() => setLater(false)}>
                    Add emergency details
                  </button>
                )}
              </div>
            )}
          </div>

          <aside className="track-side" aria-label="Status">
            <StatusTracker sos={sos} />
            <AssignedProvider sos={sos} />
            <div className="map-pane track-map">
              <BaseMap center={sos} zoom={14} label="Map: your request and the responder">
                <FitPoints points={points} fitKey={points.length} maxZoom={15} />
                <Marker position={[sos.latitude, sos.longitude]} icon={sosIcon(sos.severity?.level, sos.status, true)} keyboard={false} />
                {sos.assigned_provider && (
                  <Marker
                    position={[sos.assigned_provider.latitude, sos.assigned_provider.longitude]}
                    icon={baseIcon(sos.assigned_provider.organisation_type)}
                    keyboard={false}
                  />
                )}
              </BaseMap>
            </div>
            <p className="mono track-loc">
              {sos.location_source === "gps" ? `GPS${sos.accuracy_m ? ` ±${Math.round(sos.accuracy_m)} m` : ""}` : "Pin on map"} /{" "}
              {sos.latitude.toFixed(5)}, {sos.longitude.toFixed(5)}
            </p>
          </aside>
        </div>
      </section>
      <PrototypeNotice />
    </div>
  );
}
