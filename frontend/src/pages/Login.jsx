import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router";
import { Field, FormError } from "../components/forms";
import { AsteriskMark } from "../components/icons";
import { Wipe } from "../components/Reveal";
import { DEMO_ACCOUNTS, ROLE_LABELS, homeFor, safeNext } from "../lib/roles";
import { checkEmail, describe, onlyErrors } from "../lib/validate";
import { useAuth, useToast } from "../state/contexts";

export default function Login() {
  const { user, login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const notice = location.state?.message ?? null;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(null); // "form" or the role of a demo button
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  if (user && !busy) return <Navigate to={next ?? homeFor(user)} replace />;

  async function signIn(credentials, source) {
    const errors = onlyErrors({
      email: checkEmail(credentials.email),
      password: credentials.password ? null : "Enter your password.",
    });
    setFieldErrors(errors);
    setError(null);
    if (Object.keys(errors).length) return;
    setBusy(source);
    try {
      const account = await login(credentials.email, credentials.password);
      toast.success("Logged in", `${account.full_name} / ${ROLE_LABELS[account.role]}`);
      navigate(next ?? homeFor(account), { replace: true });
    } catch (err) {
      setError(err.status === 401 || err.status === 403 || err.status === 429 ? err.message : `Login failed: ${err.message}`);
      setBusy(null);
    }
  }

  const demoLogin = (account) => {
    setEmail(account.email);
    setPassword(account.password);
    signIn(account, account.role);
  };

  return (
    <div className="auth">
      <section className="sec sec--black auth-side" aria-labelledby="login-title">
        <p className="sec-bar mono">
          <span>(00) Access</span>
          <span>Accounts</span>
        </p>
        <div className="auth-side-body">
          <AsteriskMark size={44} />
          <Wipe as="h1" id="login-title" className="auth-title">
            Log in
          </Wipe>
          <p className="auth-lead">
            Citizens send SOS alerts and find help nearby. Service providers answer requests and keep their capacity up to date.
            Admins run the SOS monitor and the Command Centre.
          </p>
        </div>

        <div className="demo-logins" aria-labelledby="demo-title">
          <p id="demo-title" className="label demo-title">
            Demo login / one click per role
          </p>
          {DEMO_ACCOUNTS.map((account, i) => (
            <button
              key={account.role}
              type="button"
              className="demo-login"
              onClick={() => demoLogin(account)}
              disabled={Boolean(busy)}
              aria-label={`Demo login as ${account.label}`}
            >
              <span className="demo-login-no mono">{String(i + 1).padStart(2, "0")}</span>
              <span className="demo-login-role">{account.label}</span>
              <span className="demo-login-email mono">{account.email}</span>
              <span className="demo-login-go mono" aria-hidden="true">
                {busy === account.role ? <AsteriskMark size={14} className="asterisk loader" /> : "→"}
              </span>
            </button>
          ))}
          <p className="demo-note mono">Demo accounts only. Their passwords are public and listed in the README.</p>
        </div>
      </section>

      <section className="auth-main" aria-label="Login form">
        <form
          className="form auth-form"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            signIn({ email, password }, "form");
          }}
        >
          <p className="sec-no">01 / Your account</p>
          {notice && !error && (
            <p className="form-notice" role="status">
              {notice}
            </p>
          )}
          <FormError message={error} />

          <Field id="login-email" label="Email" error={fieldErrors.email}>
            <input
              {...describe("login-email", fieldErrors.email)}
              className="input"
              type="email"
              autoComplete="username"
              inputMode="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
            />
          </Field>

          <Field id="login-password" label="Password" error={fieldErrors.password}>
            <span className="password-field">
              <input
                {...describe("login-password", fieldErrors.password)}
                className="input"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button type="button" className="password-toggle mono" onClick={() => setShowPassword((s) => !s)} aria-pressed={showPassword}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </span>
          </Field>

          <button type="submit" className="btn btn--solid btn--lg auth-submit" disabled={Boolean(busy)}>
            {busy === "form" ? <AsteriskMark size={16} className="asterisk loader" /> : null}
            {busy === "form" ? "Logging in" : "Log in"}
            {busy !== "form" && (
              <span className="arrow" aria-hidden="true">
                &rarr;
              </span>
            )}
          </button>

          <p className="auth-switch">
            No account yet? <Link to="/register">Register as a citizen</Link> or{" "}
            <Link to="/register?as=provider">as a service provider</Link>.
          </p>
        </form>
      </section>
    </div>
  );
}
