import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { fetchMySos, sendSos } from "../../api";
import { FormError } from "../../components/forms";
import { AsteriskMark } from "../../components/icons";
import PinPicker from "../../components/maps/PinPicker";
import PrototypeNotice from "../../components/sos/PrototypeNotice";
import { StatusTracker } from "../../components/sos/StatusTracker";
import { SeverityTag, SosStatusTag } from "../../components/Tags";
import { EMERGENCY_TYPES, labelFor } from "../../constants";
import { getCurrentPosition } from "../../lib/geolocation";
import { usePolling } from "../../lib/hooks";
import { formatTime } from "../../lib/time";

const CONFIRM_GUARD_MS = 400; // a double press on SOS must not also press "Send alert"

export default function SosHome() {
  const navigate = useNavigate();
  const [step, setStep] = useState("idle"); // idle | confirm | locating | pin | sending
  const [geoProblem, setGeoProblem] = useState(null);
  const [pin, setPin] = useState(null);
  const [sendError, setSendError] = useState(null);
  const shownAt = useRef(0);
  const attempt = useRef(0);

  const mine = usePolling(fetchMySos, 10000);
  const active = (mine.data ?? []).filter((sos) => sos.status !== "RESOLVED");

  const cancel = useCallback(() => {
    attempt.current += 1; // ignore a location that arrives after cancelling
    setStep("idle");
    setGeoProblem(null);
    setSendError(null);
  }, []);

  useEffect(() => {
    if (step !== "confirm" && step !== "locating" && step !== "pin") return undefined;
    const onKey = (e) => e.key === "Escape" && cancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step, cancel]);

  const openConfirm = () => {
    shownAt.current = Date.now();
    setStep("confirm");
  };

  async function send(location) {
    setStep("sending");
    setSendError(null);
    try {
      const created = await sendSos(location);
      navigate(`/sos/${created.id}`, { state: { justSent: true } });
    } catch (err) {
      setSendError(err.message);
      setStep(location.location_source === "pin" ? "pin" : "confirm");
    }
  }

  async function locateAndSend() {
    if (Date.now() - shownAt.current < CONFIRM_GUARD_MS) return;
    const ticket = ++attempt.current;
    setStep("locating");
    setGeoProblem(null);
    try {
      const point = await getCurrentPosition();
      if (ticket !== attempt.current) return;
      await send({ latitude: point.latitude, longitude: point.longitude, location_source: "gps", accuracy_m: point.accuracy });
    } catch (err) {
      if (ticket !== attempt.current) return;
      setGeoProblem(err.message);
      setStep("pin");
    }
  }

  const choosePin = () => {
    attempt.current += 1;
    setGeoProblem(null);
    setStep("pin");
  };

  return (
    <div className="sos-page">
      <section className="sec sos-hero" aria-labelledby="sos-title">
        <p className="sec-bar mono">
          <span>(01) SOS</span>
          <span>Citizen dashboard</span>
        </p>

        <div className="sos-grid">
          <div className="sos-stage">
            <h1 id="sos-title" className="visually-hidden">
              Send an SOS
            </h1>

            {step === "idle" && (
              <button type="button" className="sos-button" onClick={openConfirm} aria-describedby="sos-help">
                <span className="sos-button-ring" aria-hidden="true" />
                <span className="sos-button-label">SOS</span>
                <span className="sos-button-sub mono">Press for help</span>
              </button>
            )}

            {step === "confirm" && (
              <div className="sos-panel sos-panel--confirm" role="alertdialog" aria-labelledby="confirm-title" aria-describedby="confirm-desc">
                <p className="sec-no">01 / Confirm</p>
                <h2 id="confirm-title" className="sos-panel-title">
                  Send emergency alert?
                </h2>
                <p id="confirm-desc" className="sos-panel-text">
                  Your location is shared with responders straight away. You can add the details next.
                </p>
                <FormError message={sendError} />
                <div className="sos-panel-actions">
                  <button type="button" className="sos-send" onClick={locateAndSend} autoFocus>
                    Send alert
                  </button>
                  <button type="button" className="btn btn--lg sos-cancel" onClick={cancel}>
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {step === "locating" && (
              <div className="sos-panel" role="status">
                <p className="sec-no">02 / Location</p>
                <h2 className="sos-panel-title">
                  <AsteriskMark size={34} className="asterisk loader" /> Finding your location
                </h2>
                <p className="sos-panel-text">Allow location access if your browser asks.</p>
                <div className="sos-panel-actions">
                  <button type="button" className="btn btn--lg" onClick={choosePin}>
                    Choose on the map instead
                  </button>
                  <button type="button" className="btn btn--lg sos-cancel" onClick={cancel}>
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {step === "sending" && (
              <div className="sos-panel" role="status">
                <p className="sec-no">03 / Sending</p>
                <h2 className="sos-panel-title">
                  <AsteriskMark size={34} className="asterisk loader" /> Sending your alert
                </h2>
              </div>
            )}

            {step === "pin" && (
              <div className="sos-panel sos-panel--pin">
                <p className="sec-no">02 / Location</p>
                <h2 className="sos-panel-title sos-panel-title--sm">Drop a pin where you are</h2>
                {geoProblem && (
                  <p className="form-notice" role="alert">
                    {geoProblem} Tap the map where you are instead.
                  </p>
                )}
                <FormError message={sendError} />
                <PinPicker value={pin} onChange={setPin} label="Map: drop a pin where you are" />
                <div className="sos-panel-actions">
                  <button
                    type="button"
                    className="sos-send"
                    disabled={!pin}
                    onClick={() => send({ latitude: pin.latitude, longitude: pin.longitude, location_source: "pin" })}
                  >
                    Send alert from this pin
                  </button>
                  <button type="button" className="btn btn--lg" onClick={locateAndSend}>
                    Try GPS again
                  </button>
                  <button type="button" className="btn btn--lg sos-cancel" onClick={cancel}>
                    Cancel
                  </button>
                </div>
              </div>
            )}

            <p id="sos-help" className="sos-help mono">
              Press SOS, confirm, and your location is sent at once. Details follow.
            </p>
          </div>

          <aside className="sos-aside" aria-label="Your requests and shortcuts">
            <div className="sos-aside-block">
              <p className="label">Active requests</p>
              {mine.loading && !mine.data ? (
                <p className="mono sos-empty">Loading…</p>
              ) : mine.error && !mine.data ? (
                <p className="mono sos-empty">Could not load your requests: {mine.error}</p>
              ) : active.length === 0 ? (
                <p className="mono sos-empty">No active requests.</p>
              ) : (
                <ul className="sos-active-list">
                  {active.map((sos) => (
                    <li key={sos.id}>
                      <Link to={`/sos/${sos.id}`} className="sos-active">
                        <span className="sos-active-head">
                          <span className="mono">#{sos.id}</span>
                          <SosStatusTag status={sos.status} />
                          <SeverityTag severity={sos.severity} />
                        </span>
                        <span className="sos-active-title">
                          {sos.emergency_type ? labelFor(EMERGENCY_TYPES, sos.emergency_type) : "Details not sent yet"}
                        </span>
                        <span className="mono sos-active-meta">
                          Sent {formatTime(sos.created_at)}
                          {sos.assigned_provider ? ` / ${sos.assigned_provider.organisation_name}` : ""}
                        </span>
                        <StatusTracker sos={sos} compact />
                        <span className="sos-active-go mono">Open tracker &rarr;</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="sos-aside-block">
              <p className="label">How it works</p>
              <ol className="sos-howto mono">
                <li>
                  <span>01</span> Press SOS and confirm
                </li>
                <li>
                  <span>02</span> Your location is sent at once (GPS, or a pin you drop)
                </li>
                <li>
                  <span>03</span> Add details: type, people, injuries, needs
                </li>
                <li>
                  <span>04</span> Follow the status as responders act
                </li>
              </ol>
            </div>
            <nav className="sos-shortcuts" aria-label="Citizen shortcuts">
              <Link to="/resources" className="shortcut">
                <span className="mono">02</span> Nearby resources <span aria-hidden="true">&rarr;</span>
              </Link>
              <Link to="/requests" className="shortcut">
                <span className="mono">03</span> My requests <span aria-hidden="true">&rarr;</span>
              </Link>
            </nav>
          </aside>
        </div>
      </section>
      <PrototypeNotice />
    </div>
  );
}
