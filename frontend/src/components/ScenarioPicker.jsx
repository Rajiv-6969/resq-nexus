import { useRef } from "react";
import { DISASTER_META } from "../constants";

const pad2 = (n) => String(n).padStart(2, "0");

// Scenario selector: one numbered cell per scenario (arrow keys move the choice).
export default function ScenarioPicker({ scenarios, scenarioId, onSelect, failed }) {
  const groupRef = useRef(null);

  if (!scenarios.length) {
    return (
      <div className={`picker ${failed ? "picker--failed" : "picker--loading"}`} role="status">
        {failed ? "Scenarios unavailable" : [0, 1, 2].map((i) => <span key={i} className="picker-skeleton" />)}
      </div>
    );
  }

  const onKeyDown = (event) => {
    const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
    if (!(event.key in keys)) return;
    event.preventDefault();
    const index = scenarios.findIndex((s) => s.id === scenarioId);
    const next = scenarios[(index + keys[event.key] + scenarios.length) % scenarios.length];
    onSelect(next.id);
    window.requestAnimationFrame(() => groupRef.current?.querySelector(`[data-id="${CSS.escape(next.id)}"]`)?.focus());
  };

  return (
    <div className="picker" role="radiogroup" aria-label="Disaster scenario" ref={groupRef} onKeyDown={onKeyDown}>
      {scenarios.map((s, i) => {
        const meta = DISASTER_META[s.disaster_type];
        const active = s.id === scenarioId;
        return (
          <button
            key={s.id}
            data-id={s.id}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            className={`picker-option${active ? " is-active" : ""}`}
            onClick={() => onSelect(s.id)}
            title={`${s.name} (${s.region})`}
          >
            <span className="picker-no">{pad2(i + 1)}</span>
            <span className="picker-text">
              <strong>{meta?.label ?? s.disaster_type}</strong>
              <span>{s.state}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
