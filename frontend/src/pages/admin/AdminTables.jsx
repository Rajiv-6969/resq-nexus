import { useCallback, useRef, useState } from "react";
import { approveProvider, deleteResource, fetchAdminProviders, fetchAdminResources, fetchAdminUsers, rejectProvider, updateResource, updateUser } from "../../api";
import { ResourceGlyph } from "../../components/Glyphs";
import { RESOURCE_META, RESOURCE_STATUSES } from "../../constants";
import { usePolling } from "../../lib/hooks";
import { ROLE_LABELS } from "../../lib/roles";
import { formatTime } from "../../lib/time";
import { useAuth, useToast } from "../../state/contexts";

// Shared frame for the admin tables: section bar, title, filter chips, then the table.
function TablePage({ no, title, count, filters, children, error }) {
  return (
    <section className="sec list-page" aria-labelledby="table-title">
      <p className="sec-bar mono">
        <span>
          ({no}) {title}
        </span>
        <span>{count == null ? "…" : `${count} shown`}</span>
      </p>
      <div className="list-head">
        <h1 id="table-title" className="list-title">
          {title}
        </h1>
        {filters}
      </div>
      {error && <p className="list-empty mono">Could not load: {error}</p>}
      <div className="table-wrap">{children}</div>
    </section>
  );
}

function FilterChips({ options, value, onChange, label }) {
  return (
    <div className="chips" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} className={`chip${value === o.value ? " is-on" : ""}`} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

// Runs an admin action with a toast, then reloads the table.
function useAction(refresh) {
  const toast = useToast();
  const [busy, setBusy] = useState(null);
  const run = async (key, task, success) => {
    setBusy(key);
    try {
      await task();
      toast.success(...success);
    } catch (err) {
      toast.error("Not saved", err.message);
    } finally {
      setBusy(null);
      refresh();
    }
  };
  return { busy, run };
}

// A filtered list that reloads when its filter changes.
function useFiltered(fetcher, initial) {
  const [filter, setFilter] = useState(initial);
  const ref = useRef(initial);
  const load = useCallback((options) => fetcher(ref.current, options), [fetcher]);
  const list = usePolling(load, 0);
  const change = (value) => {
    setFilter(value);
    ref.current = value;
    list.refresh();
  };
  return { filter, change, list };
}

// ------------------------------------------------------------------ providers
const PROVIDER_FILTERS = [
  { value: "PENDING", label: "Pending" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "", label: "All" },
];

export function AdminProviders() {
  const { filter, change, list } = useFiltered(fetchAdminProviders, "PENDING");
  const { busy, run } = useAction(list.refresh);
  const rows = list.data ?? [];
  return (
    <TablePage no="03" title="Providers" count={list.data ? rows.length : null} error={list.error} filters={<FilterChips options={PROVIDER_FILTERS} value={filter} onChange={change} label="Filter by approval" />}>
      <table className="table">
        <thead>
          <tr>
            <th>Organisation</th>
            <th>Contact</th>
            <th>Region</th>
            <th>Registered</th>
            <th>Status</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} className="mono table-empty">
                {filter === "PENDING" ? "No registrations are waiting for approval." : "Nothing to show."}
              </td>
            </tr>
          )}
          {rows.map((p) => (
            <tr key={p.id}>
              <td>
                <span className="cell-strong">{p.organisation_name}</span>
                <span className="cell-sub mono">{RESOURCE_META[p.organisation_type]?.org}</span>
              </td>
              <td>
                {p.contact.full_name}
                <span className="cell-sub mono">
                  {p.contact.email}
                  {p.contact.phone ? ` / ${p.contact.phone}` : ""}
                </span>
              </td>
              <td>{p.region ?? p.address ?? "—"}</td>
              <td className="mono">{formatTime(p.created_at)}</td>
              <td>
                <span className={`tag tag--approval is-${p.approval_status.toLowerCase()}`}>{p.approval_status}</span>
              </td>
              <td className="cell-actions">
                {p.approval_status !== "APPROVED" && (
                  <button type="button" className="btn btn--sm btn--solid" disabled={busy === p.id} onClick={() => run(p.id, () => approveProvider(p.id), ["Approved", `${p.organisation_name} can now respond to requests.`])}>
                    Approve
                  </button>
                )}
                {p.approval_status === "PENDING" && (
                  <button type="button" className="btn btn--sm btn--red" disabled={busy === p.id} onClick={() => run(p.id, () => rejectProvider(p.id), ["Rejected", `${p.organisation_name} was not approved.`])}>
                    Reject
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TablePage>
  );
}

// ------------------------------------------------------------------ resources
const REGION_FILTERS = [
  { value: "", label: "All regions" },
  { value: "Bengaluru", label: "Bengaluru" },
  { value: "Kachchh", label: "Kachchh" },
  { value: "Barpeta and Nalbari", label: "Barpeta" },
  { value: "Almora and Bageshwar", label: "Almora" },
];
const fetchByRegion = (region, options) => fetchAdminResources({ region: region || undefined }, options);

export function AdminResources() {
  const { filter, change, list } = useFiltered(fetchByRegion, "");
  const { busy, run } = useAction(list.refresh);
  const rows = list.data ?? [];
  return (
    <TablePage no="04" title="Resources" count={list.data ? rows.length : null} error={list.error} filters={<FilterChips options={REGION_FILTERS} value={filter} onChange={change} label="Filter by region" />}>
      <table className="table">
        <thead>
          <tr>
            <th>Resource</th>
            <th>Region</th>
            <th>Provider</th>
            <th className="num-col">Available</th>
            <th>Status</th>
            <th>Updated</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <span className="cell-glyph">
                  <ResourceGlyph type={r.resource_type} status={r.status} size={20} />
                  <span>
                    <span className="cell-strong">{r.name}</span>
                    <span className="cell-sub mono">{r.type_label}</span>
                  </span>
                </span>
              </td>
              <td>
                {r.region ?? "—"}
                <span className="cell-sub mono">{r.area}</span>
              </td>
              <td>{r.provider?.organisation_name ?? <span className="mono cell-sub">Unlinked</span>}</td>
              <td className="num-col mono">
                {r.capacity_available.toLocaleString("en-IN")} / {r.capacity_total.toLocaleString("en-IN")}
                <span className="cell-sub">{r.unit}</span>
              </td>
              <td>
                <div className="chips segmented segmented--sm" role="radiogroup" aria-label={`${r.name} status`}>
                  {RESOURCE_STATUSES.map((st) => (
                    <button
                      key={st}
                      type="button"
                      role="radio"
                      aria-checked={r.status === st}
                      className={`chip${r.status === st ? " is-on" : ""}`}
                      disabled={busy === r.id}
                      onClick={() => r.status !== st && run(r.id, () => updateResource(r.id, { status: st }), ["Status changed", `${r.name} is now ${st}.`])}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </td>
              <td className="mono">{formatTime(r.updated_at)}</td>
              <td className="cell-actions">
                <button
                  type="button"
                  className="btn btn--sm btn--red"
                  disabled={busy === r.id}
                  onClick={() => window.confirm(`Delete ${r.name}?`) && run(r.id, () => deleteResource(r.id), ["Deleted", `${r.name} was removed.`])}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TablePage>
  );
}

// ------------------------------------------------------------------ users
const ROLE_FILTERS = [
  { value: "", label: "All" },
  { value: "CITIZEN", label: "Citizens" },
  { value: "SERVICE_PROVIDER", label: "Service providers" },
  { value: "ADMIN", label: "Admins" },
];

export function AdminUsers() {
  const { user: me } = useAuth();
  const { filter, change, list } = useFiltered(fetchAdminUsers, "");
  const { busy, run } = useAction(list.refresh);
  const rows = list.data ?? [];
  return (
    <TablePage no="05" title="Users" count={list.data ? rows.length : null} error={list.error} filters={<FilterChips options={ROLE_FILTERS} value={filter} onChange={change} label="Filter by role" />}>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Role</th>
            <th>Organisation</th>
            <th>Joined</th>
            <th>Account</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((u) => (
            <tr key={u.id} className={u.is_active ? "" : "is-inactive"}>
              <td>
                <span className="cell-strong">{u.full_name}</span>
                <span className="cell-sub mono">{u.email}</span>
              </td>
              <td className="mono">{ROLE_LABELS[u.role]}</td>
              <td>{u.provider?.organisation_name ?? "—"}</td>
              <td className="mono">{formatTime(u.created_at)}</td>
              <td>
                <span className={`tag tag--approval ${u.is_active ? "is-approved" : "is-rejected"}`}>{u.is_active ? "Active" : "Deactivated"}</span>
              </td>
              <td className="cell-actions">
                {u.id !== me.id && (
                  <button
                    type="button"
                    className={`btn btn--sm${u.is_active ? " btn--red" : ""}`}
                    disabled={busy === u.id}
                    onClick={() => run(u.id, () => updateUser(u.id, { is_active: !u.is_active }), [u.is_active ? "Deactivated" : "Reactivated", u.full_name])}
                  >
                    {u.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TablePage>
  );
}
