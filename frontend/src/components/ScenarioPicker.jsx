import { useRef } from "react";
import { motion } from "framer-motion";
import { DISASTER_META } from "../constants";
import { DISASTER_ICONS } from "./iconMaps";

// Scenario selector: one card per scenario with its disaster-type icon (arrow keys move the choice).
export default function ScenarioPicker({ scenarios, scenarioId, onSelect, failed, layoutGroup = "picker" }) {
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
      {scenarios.map((s) => {
        const Icon = DISASTER_ICONS[s.disaster_type];
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
            style={{ "--accent": meta?.color ?? "#2EC4B6" }}
            onClick={() => onSelect(s.id)}
            title={`${s.name} (${s.region})`}
          >
            {active && <motion.span layoutId={`${layoutGroup}-active`} className="picker-active" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
            <span className="picker-icon">{Icon && <Icon size={18} />}</span>
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
