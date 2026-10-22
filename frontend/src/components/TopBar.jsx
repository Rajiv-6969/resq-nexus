import { CheckIcon, ChevronIcon, LogoMark } from "./icons";
import { PIPELINE } from "../constants";

function PipelineStepper() {
  return (
    <ol className="pipeline" aria-label="Decision pipeline">
      {PIPELINE.map((step, i) => (
        <li key={step.name} className={`pipeline-step ${step.status}`}>
          {i > 0 && <ChevronIcon size={14} className="pipeline-sep" />}
          <span className="pipeline-dot">{step.status === "done" ? <CheckIcon size={12} /> : i + 1}</span>
          <span className="pipeline-name">{step.name}</span>
          {step.status === "current" && <span className="visually-hidden"> (current stage)</span>}
          {step.status === "next" && <span className="visually-hidden"> (next stage)</span>}
        </li>
      ))}
    </ol>
  );
}

export default function TopBar({ scenarios, scenarioId, onScenarioChange, failed }) {
  return (
    <header className="topbar">
      <div className="brand">
        <LogoMark />
        <div className="brand-text">
          <span className="brand-name">ResQ Nexus</span>
          <span className="brand-tagline">Intelligent Disaster Response &amp; Resource Allocation</span>
        </div>
      </div>

      <PipelineStepper />

      <label className="scenario-picker">
        <span>Scenario</span>
        <select
          value={scenarioId ?? ""}
          onChange={(e) => onScenarioChange(e.target.value)}
          disabled={scenarios.length === 0}
        >
          {scenarios.length === 0 && <option value="">{failed ? "Scenarios unavailable" : "Loading scenarios…"}</option>}
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}
