import { useState } from "react";
import { RESOURCE_META } from "../../constants";
import { formatTime } from "../../lib/time";
import { useAuth, useToast } from "../../state/contexts";
import { AsteriskMark } from "../icons";

// Provider pages open only once an admin has approved the organisation.
export default function ProviderGate({ children }) {
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const [checking, setChecking] = useState(false);
  const provider = user.provider;
  if (provider?.approval_status === "APPROVED") return children;

  const checkAgain = async () => {
    setChecking(true);
    try {
      const fresh = await refreshUser();
      if (fresh.provider?.approval_status === "APPROVED") toast.success("Approved", "Your organisation can now respond to SOS requests.");
      else toast.info("Not yet", "An admin has not reviewed the registration yet.");
    } catch (err) {
      toast.error("Could not check", err.message);
    } finally {
      setChecking(false);
    }
  };

  const rejected = provider?.approval_status === "REJECTED";
  return (
    <section className="sec gate" aria-labelledby="gate-title">
      <p className="sec-bar mono">
        <span>(00) Service provider</span>
        <span>{rejected ? "Not approved" : "Awaiting approval"}</span>
      </p>
      <div className="gate-body">
        <p className="sec-no">{provider ? `${provider.organisation_name} / ${RESOURCE_META[provider.organisation_type]?.org ?? ""}` : "No organisation"}</p>
        <h1 id="gate-title" className="list-title">
          {rejected ? "Registration not approved" : "Awaiting admin approval"}
        </h1>
        <p className="gate-text">
          {rejected
            ? "An admin reviewed this registration and did not approve it. Contact the control room if you think this is a mistake."
            : "An admin checks every new organisation before it can see and answer SOS requests. Your dashboard, requests and resources open here as soon as it is approved."}
        </p>
        {rejected && provider.review_note && <p className="form-notice">Note from the admin: {provider.review_note}</p>}
        <p className="mono gate-meta">
          Registered {formatTime(provider?.created_at)}
          {provider?.reviewed_at ? ` / reviewed ${formatTime(provider.reviewed_at)}` : ""}
        </p>
        {!rejected && (
          <button type="button" className="btn btn--solid btn--lg" onClick={checkAgain} disabled={checking}>
            {checking && <AsteriskMark size={16} className="asterisk loader" />}
            Check again
          </button>
        )}
      </div>
    </section>
  );
}
