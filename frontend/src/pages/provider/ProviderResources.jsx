import { useState } from "react";
import { fetchProviderResources, updateProviderResource } from "../../api";
import CapacityBar from "../../components/CapacityBar";
import { FormError } from "../../components/forms";
import { ResourceGlyph } from "../../components/Glyphs";
import { AsteriskMark } from "../../components/icons";
import PageLoader from "../../components/PageLoader";
import ProviderGate from "../../components/provider/ProviderGate";
import { ResourceStatusTag } from "../../components/Tags";
import { RESOURCE_STATUSES } from "../../constants";
import { useNow, usePolling } from "../../lib/hooks";
import { formatCount } from "../../lib/resources";
import { timeAgo } from "../../lib/time";
import { useToast } from "../../state/contexts";

const MAX = 1000000;
const STATUS_HELP = { OPEN: "Taking people / requests", FULL: "Open but no capacity left", CLOSED: "Not operating" };

const toForm = (r) => ({ capacity_available: String(r.capacity_available), capacity_total: String(r.capacity_total), status: r.status });
const wholeNumber = (text) => (/^\d+$/.test(text.trim()) ? Number(text) : NaN);

function checkCapacity(form) {
  const errors = {};
  const total = wholeNumber(form.capacity_total);
  const available = wholeNumber(form.capacity_available);
  if (!Number.isInteger(total) || total > MAX) errors.capacity_total = `Enter a whole number from 0 to ${formatCount(MAX)}.`;
  if (!Number.isInteger(available) || available > MAX) errors.capacity_available = `Enter a whole number from 0 to ${formatCount(MAX)}.`;
  else if (Number.isInteger(total) && available > total) errors.capacity_available = `Available cannot be more than the total (${formatCount(total)}).`;
  return errors;
}

// One resource: available / total capacity and OPEN / FULL / CLOSED, saved with PATCH.
function ResourceEditor({ resource, now, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState(() => toForm(resource));
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [base, setBase] = useState(resource);
  // A newer copy from the server (after a save or refresh) resets the form if it was untouched.
  if (resource !== base) {
    const untouched = JSON.stringify(form) === JSON.stringify(toForm(base));
    setBase(resource);
    if (untouched) setForm(toForm(resource));
  }

  const dirty = JSON.stringify(form) !== JSON.stringify(toForm(resource));
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const step = (key, delta) => {
    const value = wholeNumber(form[key]);
    set(key, String(Math.max(0, Math.min(MAX, (Number.isInteger(value) ? value : 0) + delta))));
  };
  const preview = { available: wholeNumber(form.capacity_available), total: wholeNumber(form.capacity_total) };

  async function save(e) {
    e.preventDefault();
    const found = checkCapacity(form);
    setErrors(found);
    setError(null);
    if (Object.keys(found).length) return;
    const changes = {};
    if (Number(form.capacity_total) !== resource.capacity_total) changes.capacity_total = Number(form.capacity_total);
    if (Number(form.capacity_available) !== resource.capacity_available) changes.capacity_available = Number(form.capacity_available);
    if (form.status !== resource.status) changes.status = form.status;
    setBusy(true);
    try {
      const saved = await updateProviderResource(resource.id, changes);
      onSaved(saved);
      toast.success("Saved", `${saved.name}: ${formatCount(saved.capacity_available)} of ${formatCount(saved.capacity_total)} ${saved.unit}, ${saved.status}.`);
    } catch (err) {
      setErrors(err.fieldErrors ?? {});
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const id = `r${resource.id}`;
  return (
    <form className={`res-editor${dirty ? " is-dirty" : ""}`} onSubmit={save} noValidate aria-labelledby={`${id}-name`}>
      <div className="res-editor-head">
        <ResourceGlyph type={resource.resource_type} status={form.status} size={30} />
        <div>
          <h2 id={`${id}-name`} className="res-editor-name">
            {resource.name}
          </h2>
          <p className="mono res-editor-type">
            {resource.type_label}
            {resource.area ? ` / ${resource.area}` : ""} / updated {timeAgo(resource.updated_at, now)}
          </p>
        </div>
        <ResourceStatusTag status={resource.status} />
      </div>

      <FormError message={error} />
      <div className="res-editor-grid">
        {[
          ["capacity_available", `Available ${resource.unit}`],
          ["capacity_total", `Total ${resource.unit}`],
        ].map(([key, label]) => (
          <div className="field" key={key}>
            <label className="field-label" htmlFor={`${id}-${key}`}>
              {label}
            </label>
            <span className="stepper-input">
              <button type="button" onClick={() => step(key, -1)} aria-label={`${label}: one less`}>
                &minus;
              </button>
              <input
                id={`${id}-${key}`}
                className="input input--num"
                inputMode="numeric"
                value={form[key]}
                aria-invalid={errors[key] ? true : undefined}
                onChange={(e) => set(key, e.target.value.replace(/[^\d]/g, "").slice(0, 7))}
              />
              <button type="button" onClick={() => step(key, 1)} aria-label={`${label}: one more`}>
                +
              </button>
            </span>
            {errors[key] && <p className="field-error">{errors[key]}</p>}
          </div>
        ))}
        <fieldset className="field field--group">
          <legend className="field-label">Status</legend>
          <div className="chips segmented" role="radiogroup" aria-label={`${resource.name} status`}>
            {RESOURCE_STATUSES.map((status) => (
              <button
                key={status}
                type="button"
                role="radio"
                aria-checked={form.status === status}
                className={`chip chip--${status.toLowerCase()}${form.status === status ? " is-on" : ""}`}
                onClick={() => set("status", status)}
                title={STATUS_HELP[status]}
              >
                {status}
              </button>
            ))}
          </div>
        </fieldset>
      </div>

      <div className="res-editor-foot">
        <div className="res-editor-preview">
          <CapacityBar available={Number.isInteger(preview.available) ? preview.available : 0} total={Number.isInteger(preview.total) ? preview.total : 0} />
          <p className="mono">
            {Number.isInteger(preview.available) && Number.isInteger(preview.total) ? `${formatCount(preview.available)} of ${formatCount(preview.total)} ${resource.unit} available` : "—"}
          </p>
        </div>
        <button
          type="button"
          className="btn"
          onClick={() => {
            setForm(toForm(resource));
            setErrors({});
            setError(null);
          }}
          disabled={!dirty || busy}
        >
          Undo
        </button>
        <button type="submit" className="btn btn--solid" disabled={!dirty || busy}>
          {busy && <AsteriskMark size={14} className="asterisk loader" />}
          Save
        </button>
      </div>
    </form>
  );
}

function ResourceBoard() {
  const now = useNow(30000);
  const list = usePolling(fetchProviderResources, 0);
  if (!list.data && list.loading) return <PageLoader label="Loading your resources" />;
  const resources = list.data ?? [];
  const replaceOne = (saved) => list.replace((items) => items.map((r) => (r.id === saved.id ? saved : r)));

  return (
    <section className="sec list-page" aria-labelledby="myres-title">
      <p className="sec-bar mono">
        <span>(03) My resources</span>
        <span>{resources.length} listed</span>
      </p>
      <div className="list-head">
        <h1 id="myres-title" className="list-title">
          My resources
        </h1>
        <p className="list-lead">
          Keep these figures current: citizens see them on Nearby Resources, and admins use them to suggest who should respond.
        </p>
      </div>
      {list.error && <p className="list-empty mono">Could not load your resources: {list.error}</p>}
      {resources.length === 0 && !list.error && <p className="list-empty mono">No resources are listed for your organisation yet. Ask an admin to add one.</p>}
      <div className="res-editors">
        {resources.map((resource) => (
          <ResourceEditor key={resource.id} resource={resource} now={now} onSaved={replaceOne} />
        ))}
      </div>
    </section>
  );
}

export default function ProviderResources() {
  return (
    <ProviderGate>
      <ResourceBoard />
    </ProviderGate>
  );
}
