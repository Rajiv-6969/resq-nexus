import { useCallback, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { ChoiceChips, Field, FormError } from "../components/forms";
import { AsteriskMark } from "../components/icons";
import PinPicker from "../components/maps/PinPicker";
import { Wipe } from "../components/Reveal";
import { RESOURCE_META, RESOURCE_TYPES } from "../constants";
import { getCurrentPosition } from "../lib/geolocation";
import { homeFor } from "../lib/roles";
import { checkEmail, checkLength, checkName, checkPassword, checkPhone, describe, onlyErrors, squash } from "../lib/validate";
import { useAuth, useToast } from "../state/contexts";

const KINDS = [
  { value: "citizen", label: "Citizen" },
  { value: "provider", label: "Service provider" },
];
const ORG_TYPES = RESOURCE_TYPES.map((type) => ({ value: type, label: RESOURCE_META[type].org }));
const EMPTY = { full_name: "", email: "", password: "", phone: "", organisation_name: "", organisation_type: "", address: "" };

export default function Register() {
  const { user, register, registerProvider } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const kind = params.get("as") === "provider" ? "provider" : "citizen";
  const provider = kind === "provider";

  const [form, setForm] = useState(EMPTY);
  const [location, setLocation] = useState(null);
  const [focus, setFocus] = useState(null);
  const [locating, setLocating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const choosePoint = useCallback((point) => {
    setLocation(point);
    setFieldErrors((errors) => ({ ...errors, latitude: undefined }));
  }, []);

  if (user && !busy) return <Navigate to={homeFor(user)} replace />;
  const locationError = fieldErrors.latitude || fieldErrors.longitude;

  const switchKind = (value) => {
    setParams(value === "provider" ? { as: "provider" } : {}, { replace: true });
    setFieldErrors({});
    setError(null);
  };

  const useMyLocation = async () => {
    setLocating(true);
    try {
      const point = await getCurrentPosition();
      const chosen = { latitude: point.latitude, longitude: point.longitude };
      choosePoint(chosen);
      setFocus(chosen);
    } catch (err) {
      toast.warning("Location unavailable", `${err.message} Drop a pin on the map instead.`);
    } finally {
      setLocating(false);
    }
  };

  function validate() {
    return onlyErrors({
      full_name: checkName(form.full_name),
      email: checkEmail(form.email),
      password: checkPassword(form.password),
      phone: checkPhone(form.phone, { required: provider }),
      ...(provider && {
        organisation_name: checkLength(form.organisation_name, { min: 2, max: 120, label: "Organisation name" }),
        organisation_type: form.organisation_type ? null : "Choose the organisation type.",
        latitude: location ? null : "Drop a pin where the organisation is based.",
        address: checkLength(form.address, { max: 160, label: "Address" }),
      }),
    });
  }

  async function submit(e) {
    e.preventDefault();
    const errors = validate();
    setFieldErrors(errors);
    setError(Object.keys(errors).length ? "Please correct the highlighted fields." : null);
    if (Object.keys(errors).length) return;

    const body = {
      full_name: squash(form.full_name),
      email: form.email.trim(),
      password: form.password,
      phone: squash(form.phone) || null,
    };
    setBusy(true);
    try {
      if (provider) {
        const data = await registerProvider({
          ...body,
          organisation_name: squash(form.organisation_name),
          organisation_type: form.organisation_type,
          latitude: location.latitude,
          longitude: location.longitude,
          address: squash(form.address) || null,
        });
        toast.success("Registration received", data.message);
        navigate(homeFor(data.user), { replace: true });
      } else {
        const account = await register(body);
        toast.success("Account created", `Welcome, ${account.full_name}.`);
        navigate(homeFor(account), { replace: true });
      }
    } catch (err) {
      const fromServer = { ...err.fieldErrors };
      if (err.status === 409) fromServer.email = err.message;
      setFieldErrors(fromServer);
      setError(err.message);
      setBusy(false);
    }
  }

  const input = (key, props = {}) => (
    <input {...describe(`reg-${key}`, fieldErrors[key], props.hint)} className="input" value={form[key]} onChange={set(key)} {...props.attrs} />
  );

  return (
    <div className="auth auth--register">
      <section className="sec sec--black auth-side" aria-labelledby="register-title">
        <p className="sec-bar mono">
          <span>(00) Access</span>
          <span>New account</span>
        </p>
        <div className="auth-side-body">
          <AsteriskMark size={44} />
          <Wipe as="h1" id="register-title" className="auth-title">
            Register
          </Wipe>
          <p className="auth-lead">
            {provider
              ? "Hospitals, ambulance services, shelters, food and water points, fire and police stations register their organisation. An admin checks and approves it before you can respond to SOS requests."
              : "Create a citizen account to send SOS alerts, follow their status and find hospitals, shelters and other help near you."}
          </p>
        </div>
        <ol className="auth-steps mono">
          <li>
            <span>01</span> Your details
          </li>
          {provider && (
            <li>
              <span>02</span> Organisation and location
            </li>
          )}
          <li>
            <span>{provider ? "03" : "02"}</span> {provider ? "Admin approval" : "Straight to your SOS dashboard"}
          </li>
        </ol>
      </section>

      <section className="auth-main" aria-label="Registration form">
        <form className="form auth-form" noValidate onSubmit={submit}>
          <ChoiceChips id="reg-kind" label="I am registering as" options={KINDS} value={kind} onChange={switchKind} size="lg" />
          <FormError message={error} />

          <p className="sec-no">01 / Your details</p>
          <Field id="reg-full_name" label="Full name" error={fieldErrors.full_name}>
            {input("full_name", { attrs: { autoComplete: "name" } })}
          </Field>
          <Field id="reg-email" label="Email" error={fieldErrors.email}>
            {input("email", { attrs: { type: "email", autoComplete: "email", inputMode: "email" } })}
          </Field>
          <Field id="reg-password" label="Password" error={fieldErrors.password} hint="At least 8 characters, with a letter and a number.">
            {input("password", { hint: true, attrs: { type: "password", autoComplete: "new-password" } })}
          </Field>
          <Field id="reg-phone" label="Phone" optional={!provider} error={fieldErrors.phone} hint={provider ? "Requests will show this number." : "Pre-filled in your SOS details."}>
            {input("phone", { hint: true, attrs: { type: "tel", autoComplete: "tel", inputMode: "tel" } })}
          </Field>

          {provider && (
            <>
              <p className="sec-no">02 / Organisation</p>
              <Field id="reg-organisation_name" label="Organisation name" error={fieldErrors.organisation_name}>
                {input("organisation_name", { attrs: { autoComplete: "organization" } })}
              </Field>
              <ChoiceChips
                id="reg-organisation_type"
                label="Organisation type"
                options={ORG_TYPES}
                value={form.organisation_type}
                onChange={(value) => setForm((f) => ({ ...f, organisation_type: value }))}
                error={fieldErrors.organisation_type}
              />
              <div className="field">
                <p className="field-label">
                  <span>Location</span>
                  <button type="button" className="btn btn--sm" onClick={useMyLocation} disabled={locating}>
                    {locating ? "Locating…" : "Use my location"}
                  </button>
                </p>
                <PinPicker value={location} onChange={choosePoint} focus={focus} label="Map: where the organisation is based" invalid={Boolean(locationError)} />
                {locationError && <p className="field-error">{locationError}</p>}
              </div>
              <Field id="reg-address" label="Address" optional error={fieldErrors.address}>
                {input("address", { attrs: { autoComplete: "street-address" } })}
              </Field>
            </>
          )}

          <button type="submit" className="btn btn--solid btn--lg auth-submit" disabled={busy}>
            {busy && <AsteriskMark size={16} className="asterisk loader" />}
            {busy ? "Creating account" : provider ? "Register organisation" : "Create account"}
            {!busy && (
              <span className="arrow" aria-hidden="true">
                &rarr;
              </span>
            )}
          </button>
          <p className="auth-switch">
            Already registered? <Link to="/login">Log in</Link>.
          </p>
        </form>
      </section>
    </div>
  );
}
