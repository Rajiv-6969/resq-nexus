import { useState } from "react";
import { addSosDetails } from "../../api";
import { EMERGENCY_TYPES, INJURY_LEVELS, NEEDS, VULNERABLE_GROUPS } from "../../constants";
import { checkPhone, describe, onlyErrors, squash } from "../../lib/validate";
import { useAuth } from "../../state/contexts";
import { ChoiceChips, Field, FormError } from "../forms";
import { AsteriskMark } from "../icons";

const MAX_PEOPLE = 10000;

function initialValues(sos, user) {
  return {
    emergency_type: sos.emergency_type ?? "",
    people_affected: String(sos.people_affected ?? 1),
    injuries: sos.injuries ?? "",
    needs: sos.needs ?? [],
    vulnerable: sos.vulnerable ?? [],
    description: sos.description ?? "",
    contact_phone: sos.contact_phone ?? user?.phone ?? "",
  };
}

// The Emergency Details form. The request already exists (saved with its location);
// this adds what responders need to know, and can be corrected until it is resolved.
export default function SosDetailsForm({ sos, onSaved, onCancel }) {
  const { user } = useAuth();
  const [form, setForm] = useState(() => initialValues(sos, user));
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (value) => setForm((f) => ({ ...f, [key]: value }));

  const people = Number(form.people_affected);
  const stepPeople = (delta) =>
    set("people_affected")(String(Math.min(MAX_PEOPLE, Math.max(1, (Number.isFinite(people) ? Math.round(people) : 1) + delta))));

  function validate() {
    return onlyErrors({
      emergency_type: form.emergency_type ? null : "Choose the type of emergency.",
      people_affected:
        /^\d+$/.test(form.people_affected.trim()) && people >= 1 && people <= MAX_PEOPLE ? null : `Enter a whole number from 1 to ${MAX_PEOPLE}.`,
      injuries: form.injuries ? null : "Choose the level of injuries.",
      needs: form.needs.length ? null : "Choose at least one need.",
      description: squash(form.description).length > 500 ? "Description must be at most 500 characters." : null,
      contact_phone: checkPhone(form.contact_phone, { required: true }),
    });
  }

  async function submit(e) {
    e.preventDefault();
    const found = validate();
    setErrors(found);
    setError(Object.keys(found).length ? "Please complete the highlighted fields." : null);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      const saved = await addSosDetails(sos.id, {
        emergency_type: form.emergency_type,
        people_affected: people,
        injuries: form.injuries,
        needs: form.needs,
        vulnerable: form.vulnerable,
        description: squash(form.description),
        contact_phone: squash(form.contact_phone),
      });
      onSaved(saved);
    } catch (err) {
      setErrors(err.fieldErrors ?? {});
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const left = 500 - squash(form.description).length;

  return (
    <form className="form sos-form" noValidate onSubmit={submit} aria-labelledby="details-title">
      <h2 id="details-title" className="sos-form-title">
        Emergency details
      </h2>
      <FormError message={error} />

      <ChoiceChips id="d-type" label="Emergency type" options={EMERGENCY_TYPES} value={form.emergency_type} onChange={set("emergency_type")} error={errors.emergency_type} />

      <Field id="d-people" label="Number of people affected" error={errors.people_affected}>
        <span className="stepper-input">
          <button type="button" onClick={() => stepPeople(-1)} aria-label="One fewer person">
            &minus;
          </button>
          <input
            {...describe("d-people", errors.people_affected)}
            className="input input--num"
            inputMode="numeric"
            value={form.people_affected}
            onChange={(e) => set("people_affected")(e.target.value.replace(/[^\d]/g, "").slice(0, 5))}
          />
          <button type="button" onClick={() => stepPeople(1)} aria-label="One more person">
            +
          </button>
        </span>
      </Field>

      <ChoiceChips id="d-injuries" label="Injuries" options={INJURY_LEVELS} value={form.injuries} onChange={set("injuries")} error={errors.injuries} />
      <ChoiceChips id="d-needs" label="Needs" options={NEEDS} value={form.needs} onChange={set("needs")} multiple error={errors.needs} />
      <ChoiceChips id="d-vulnerable" label="Vulnerable people present" options={VULNERABLE_GROUPS} value={form.vulnerable} onChange={set("vulnerable")} multiple />

      <Field id="d-description" label="Short description" optional error={errors.description} hint={`${left} characters left`}>
        <textarea
          {...describe("d-description", errors.description, true)}
          className="textarea"
          rows={3}
          maxLength={600}
          value={form.description}
          onChange={(e) => set("description")(e.target.value)}
          placeholder="What happened, landmarks, floor or building"
        />
      </Field>

      <Field id="d-phone" label="Contact phone number" error={errors.contact_phone}>
        <input
          {...describe("d-phone", errors.contact_phone)}
          className="input"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          value={form.contact_phone}
          onChange={(e) => set("contact_phone")(e.target.value)}
        />
      </Field>

      <div className="form-actions">
        <button type="submit" className="btn btn--solid btn--lg" disabled={busy}>
          {busy && <AsteriskMark size={16} className="asterisk loader" />}
          {busy ? "Sending details" : sos.details_submitted ? "Save changes" : "Send details"}
        </button>
        {onCancel && (
          <button type="button" className="btn btn--lg" onClick={onCancel} disabled={busy}>
            {sos.details_submitted ? "Cancel" : "Later"}
          </button>
        )}
      </div>
    </form>
  );
}
