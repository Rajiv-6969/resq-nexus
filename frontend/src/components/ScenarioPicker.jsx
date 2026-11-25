import { useContext, useRef } from "react";
import { DISASTER_META } from "../constants";
import { AppDataContext } from "../state/contexts";

const pad2 = (n) => String(n).padStart(2, "0");

// Scenario selector: one numbered cell per scenario (arrow keys move the choice).
export default function ScenarioPicker({
  scenarios: scenariosProp,
  scenarioId: scenarioIdProp,
  onSelect: onSelectProp,
  failed: failedProp,
} = {}) {
  const groupRef = useRef(null);
  const appData = useContext(AppDataContext);

  // Support direct props or fallback to AppDataContext
  const rawScenarios = scenariosProp !== undefined ? scenariosProp : appData?.scenarios;
  const scenarios = Array.isArray(rawScenarios) ? rawScenarios : (rawScenarios?.scenarios ?? []);
  const scenarioId = scenarioIdProp !== undefined ? scenarioIdProp : appData?.scenarioId;
  const onSelect = onSelectProp ?? appData?.selectScenario;
  const failed = failedProp !== undefined ? failedProp : (appData?.listState?.status === "error");

  if (!scenarios?.length) {
    return (
      <div className={`picker ${failed ? "picker--failed" : "picker--loading"}`} role="status">
        {failed ? "Scenarios unavailable" : [0, 1, 2].map((i) => <span key={i} className="picker-skeleton" />)}
      </div>
    );
  }

  const onKeyDown = (event) => {
    const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
    if (!(event.key in keys)) return;
    if (!scenarios?.length) return;
    event.preventDefault();
    const index = scenarios.findIndex((s) => s?.id === scenarioId);
    const validIndex = index >= 0 ? index : 0;
    const next = scenarios[(validIndex + keys[event.key] + scenarios.length) % scenarios.length];
    if (next?.id && onSelect) {
      onSelect(next.id);
      window.requestAnimationFrame(() => groupRef.current?.querySelector(`[data-id="${CSS.escape(next.id)}"]`)?.focus());
    }
  };

  return (
    <div className="picker" role="radiogroup" aria-label="Disaster scenario" ref={groupRef} onKeyDown={onKeyDown}>
      {(scenarios ?? []).map((s, i) => {
        const meta = s?.disaster_type ? DISASTER_META[s.disaster_type] : null;
        const active = s?.id != null && s.id === scenarioId;
        return (
          <button
            key={s?.id ?? i}
            data-id={s?.id}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            className={`picker-option${active ? " is-active" : ""}`}
            onClick={() => s?.id != null && onSelect?.(s.id)}
            title={s?.name ? `${s.name} (${s.region ?? ""})` : ""}
          >
            <span className="picker-no">{pad2(i + 1)}</span>
            <span className="picker-text">
              <strong>{meta?.label ?? s?.disaster_type ?? "Scenario"}</strong>
              <span>{s?.state ?? ""}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
